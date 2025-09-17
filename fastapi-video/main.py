import os
import ssl
import certifi
import urllib
import requests
import re
import cv2
import json
import shutil
from fastapi import FastAPI, Depends, BackgroundTasks, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
from database import create_db_and_tables, get_session, engine
from models import VideoJob, VideoFrameTimeseries, VideoFrameVector, AudioTranscriptChunk, FrameTranscriptAssociation
from datetime import datetime
from yt_dlp import YoutubeDL
from ultralytics import YOLO
from transformers import BlipProcessor, BlipForConditionalGeneration
from sentence_transformers import SentenceTransformer
import torch
from PIL import Image

app = FastAPI()

class VideoMediaRequest(BaseModel):
    url: str | None = None
    local_path: str | None = None

def get_video_id_from_url(url):
    if not url:
        return None
    match = re.search(r"v=([A-Za-z0-9_-]+)", url)
    return match.group(1) if match else None

def get_video_duration(youtube_url=None, local_path=None, config_path="video_config.json", fallback_default=20):
    video_id = get_video_id_from_url(youtube_url) if youtube_url else None
    duration = fallback_default
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            cfg = json.load(f)
            duration = cfg.get("default", fallback_default)
            if youtube_url and video_id and video_id in cfg:
                duration = cfg[video_id]
            elif youtube_url and youtube_url in cfg:
                duration = cfg[youtube_url]
            elif local_path and local_path in cfg:
                duration = cfg[local_path]
    return duration

@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    os.makedirs("../contents/media", exist_ok=True)

@app.post("/process_media_video/")
def process_media_video(request: VideoMediaRequest, background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
    if (request.url is None and request.local_path is None) or (request.url and request.local_path):
        raise HTTPException(status_code=400, detail="Provide exactly one of url or local_path")
    
    if request.local_path:
        if not os.path.exists(request.local_path):
            raise HTTPException(status_code=400, detail="Local file does not exist")
        if not request.local_path.lower().endswith(('.mp4', '.avi', '.mkv')):
            raise HTTPException(status_code=400, detail="Unsupported video format")
        video_name = os.path.splitext(os.path.basename(request.local_path))[0]
    else:
        video_name = get_video_id_from_url(request.url) or "unknown"
    
    job = VideoJob(url=request.url, video_name=video_name, status="pending")
    session.add(job)
    session.commit()
    session.refresh(job)
    background_tasks.add_task(process_video, job.id, request.url, request.local_path)
    return {"job_id": job.id, "url": request.url, "local_path": request.local_path, "video_name": job.video_name}

def process_video(job_id: int, youtube_url: str | None, local_path: str | None):
    with Session(engine) as session:
        job = session.get(VideoJob, job_id)
        job.status = "processing"
        session.commit()

        try:
            # Prepare paths
            video_name = job.video_name
            base_folder = f"../contents/media/{video_name}"
            os.makedirs(base_folder, exist_ok=True)
            video_file_path = f"../contents/media/{video_name}.mp4"
            frames_folder = base_folder
            json_path = os.path.join(frames_folder, "video_data.json")

            # Handle video source
            if local_path:
                # Validate and copy local file
                cap = cv2.VideoCapture(local_path)
                if not cap.isOpened():
                    raise ValueError("Error: Could not open local video file")
                cap.release()
                shutil.copy(local_path, video_file_path)
                duration = get_video_duration(local_path=local_path)
            else:
                # Download from YouTube
                requests.get(
                    'https://huggingface.co/api/models/Salesforce/blip-image-captioning-base/revision/main',
                    verify=False
                )
                os.environ['CURL_CA_BUNDLE'] = ''
                ssl._create_default_https_context = ssl._create_unverified_context
                urllib.request.urlopen("https://www.youtube.com")
                duration = get_video_duration(youtube_url)
                section_str = f"0:00-00:{duration:02d}"
                ydl_opts = {
                    "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
                    "outtmpl": video_file_path,
                    "quiet": True,
                    "noplaylist": True,
                    "nocheckcertificate": True,
                    "download_sections": [section_str],
                }
                with YoutubeDL(ydl_opts) as ydl:
                    ydl.download([youtube_url])

            # Load models
            device = "cuda" if torch.cuda.is_available() else "cpu"
            yolo_model = YOLO('yolov8n.pt')
            processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
            blip_model = BlipForConditionalGeneration.from_pretrained(
                "Salesforce/blip-image-captioning-base"
            ).to(device)
            blip_model.eval()
            embed_model = SentenceTransformer('all-MiniLM-L6-v2')

            # Process video
            cap = cv2.VideoCapture(video_file_path)
            if not cap.isOpened():
                raise ValueError("Error: Could not open video.")
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = 0
            chunk_size = int(fps * 5) if fps > 0 else 25
            chunk_captions = []
            chunk_index = 0
            all_frames_info = []
            all_chunks_info = []
            all_associations_info = []
            max_duration = float(duration)

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                timestamp = frame_count / fps if fps > 0 else frame_count / 25
                if timestamp > max_duration:
                    break

                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # YOLOv8 object detection
                yolo_results = yolo_model(frame_rgb)
                objects = [(int(box.cls), float(box.conf)) for box in yolo_results[0].boxes]
                object_names = [f"{yolo_model.names[obj]} ({conf:.2f})" for obj, conf in objects]

                # BLIP captioning
                pil_img = Image.fromarray(frame_rgb)
                inputs = processor(pil_img, return_tensors="pt").to(device)
                with torch.no_grad():
                    output_ids = blip_model.generate(**inputs, max_length=50)
                    caption = processor.decode(output_ids[0], skip_special_tokens=True)

                # Save frame image in <video_name> folder
                image_filename = f"frame_{frame_count:05d}.jpg"
                image_path = os.path.join(frames_folder, image_filename)
                cv2.imwrite(image_path, yolo_results[0].plot())

                # Save frame metadata to DB
                frame_record = VideoFrameTimeseries(
                    job_id=job.id,
                    frame_number=frame_count,
                    timestamp=timestamp,
                    image_file=image_filename,
                    objects=json.dumps(object_names),
                    caption=caption
                )
                session.add(frame_record)
                session.flush()

                # Generate and save vector embedding
                embedding = embed_model.encode(caption).tolist()
                vector_record = VideoFrameVector(
                    job_id=job.id,
                    timeseries_id=frame_record.id,
                    frame_number=frame_count,
                    vector=json.dumps(embedding),
                    caption=caption
                )
                session.add(vector_record)
                session.flush()

                chunk_captions.append(caption)
                if (frame_count + 1) % chunk_size == 0:
                    transcript = " ".join(chunk_captions)
                    start_time = (frame_count - chunk_size + 1) / fps if fps > 0 else (frame_count - chunk_size + 1) / 25
                    end_time = frame_count / fps if fps > 0 else frame_count / 25
                    chunk_record = AudioTranscriptChunk(
                        job_id=job.id,
                        chunk_index=chunk_index,
                        start_time=start_time,
                        end_time=end_time,
                        transcript=transcript
                    )
                    session.add(chunk_record)
                    session.flush()

                    # Create FrameTranscriptAssociation (bulk)
                    chunk_frames = session.exec(
                        select(VideoFrameTimeseries)
                        .where(
                            (VideoFrameTimeseries.job_id == job.id) &
                            (VideoFrameTimeseries.frame_number >= frame_count - chunk_size + 1) &
                            (VideoFrameTimeseries.frame_number <= frame_count)
                        )
                    ).all()
                    associations = [
                        FrameTranscriptAssociation(
                            frame_id=assoc_frame.id,
                            transcript_chunk_id=chunk_record.id
                        ) for assoc_frame in chunk_frames
                    ]
                    session.add_all(associations)
                    session.flush()

                    # Save chunk info for JSON
                    all_chunks_info.append({
                        "chunk_index": chunk_index,
                        "start_time": start_time,
                        "end_time": end_time,
                        "transcript": transcript
                    })

                    # Save association info for JSON
                    for assoc in associations:
                        all_associations_info.append({
                            "frame_id": assoc.frame_id,
                            "transcript_chunk_id": assoc.transcript_chunk_id
                        })

                    chunk_captions = []
                    chunk_index += 1

                # Save frame info for JSON
                all_frames_info.append({
                    "frame_number": frame_count,
                    "timestamp": timestamp,
                    "image_file": image_filename,
                    "objects": object_names,
                    "caption": caption,
                    "vector_id": vector_record.id
                })

                frame_count += 1

            # Handle leftover transcript chunk
            if chunk_captions:
                transcript = " ".join(chunk_captions)
                start_time = (frame_count - len(chunk_captions)) / fps if fps > 0 else (frame_count - len(chunk_captions)) / 25
                end_time = frame_count / fps if fps > 0 else frame_count / 25
                chunk_record = AudioTranscriptChunk(
                    job_id=job.id,
                    chunk_index=chunk_index,
                    start_time=start_time,
                    end_time=end_time,
                    transcript=transcript
                )
                session.add(chunk_record)
                session.flush()

                # Create FrameTranscriptAssociation for leftover chunk
                leftover_frames = session.exec(
                    select(VideoFrameTimeseries)
                    .where(
                        (VideoFrameTimeseries.job_id == job.id) &
                        (VideoFrameTimeseries.frame_number >= frame_count - len(chunk_captions)) &
                        (VideoFrameTimeseries.frame_number < frame_count)
                    )
                ).all()
                associations = [
                    FrameTranscriptAssociation(
                        frame_id=assoc_frame.id,
                        transcript_chunk_id=chunk_record.id
                    ) for assoc_frame in leftover_frames
                ]
                session.add_all(associations)
                session.flush()

                # Save chunk info for JSON
                all_chunks_info.append({
                    "chunk_index": chunk_index,
                    "start_time": start_time,
                    "end_time": end_time,
                    "transcript": transcript
                })

                # Save association info for JSON
                for assoc in associations:
                    all_associations_info.append({
                        "frame_id": assoc.frame_id,
                        "transcript_chunk_id": assoc.transcript_chunk_id
                    })

            cap.release()

            # Save JSON file in <video_name> folder
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump({
                    "video_name": video_name,
                    "video_file": f"{video_name}.mp4",
                    "frames": all_frames_info,
                    "transcript_chunks": all_chunks_info,
                    "frame_transcript_associations": all_associations_info,
                }, f, indent=2)

            job.status = "complete"
            job.result_json_path = json_path
            job.updated_at = datetime.utcnow()
            session.commit()

        except Exception as e:
            job.status = "error"
            job.error_msg = str(e)
            job.updated_at = datetime.utcnow()
            session.commit()
            print(f"Error processing video for job {job_id}: {e}")

@app.get("/job/{job_id}")
def get_job(job_id: int, session: Session = Depends(get_session)):
    job = session.get(VideoJob, job_id)
    return job

@app.get("/frames/{job_id}")
def get_frames(job_id: int, session: Session = Depends(get_session)):
    frames = session.exec(select(VideoFrameTimeseries).where(VideoFrameTimeseries.job_id == job_id)).all()
    return frames

@app.get("/vectors/{job_id}")
def get_vectors(job_id: int, session: Session = Depends(get_session)):
    vectors = session.exec(select(VideoFrameVector).where(VideoFrameVector.job_id == job_id)).all()
    return vectors

@app.get("/frame-vector/{frame_id}")
def get_frame_vector(frame_id: int, session: Session = Depends(get_session)):
    frame = session.get(VideoFrameTimeseries, frame_id)
    vector = session.exec(select(VideoFrameVector).where(VideoFrameVector.timeseries_id == frame_id)).first()
    return {"vector": vector, "timeseries": frame}

@app.get("/transcripts/{job_id}")
def get_transcripts(job_id: int, session: Session = Depends(get_session)):
    chunks = session.exec(select(AudioTranscriptChunk).where(AudioTranscriptChunk.job_id == job_id)).all()
    return chunks

@app.get("/frames-for-transcript/{chunk_id}")
def get_frames_for_transcript(chunk_id: int, session: Session = Depends(get_session)):
    chunk = session.get(AudioTranscriptChunk, chunk_id)
    frames = session.exec(
        select(VideoFrameTimeseries)
        .where(
            (VideoFrameTimeseries.job_id == chunk.job_id) &
            (VideoFrameTimeseries.timestamp >= chunk.start_time) &
            (VideoFrameTimeseries.timestamp < chunk.end_time)
        )
    ).all()
    return frames

@app.get("/transcript-for-frame/{frame_id}")
def get_transcript_for_frame(frame_id: int, session: Session = Depends(get_session)):
    frame = session.get(VideoFrameTimeseries, frame_id)
    chunk = session.exec(
        select(AudioTranscriptChunk)
        .where(
            (AudioTranscriptChunk.job_id == frame.job_id) &
            (AudioTranscriptChunk.start_time <= frame.timestamp) &
            (AudioTranscriptChunk.end_time > frame.timestamp)
        )
    ).first()
    return chunk

@app.get("/frame-transcript-associations/{job_id}")
def get_frame_transcript_associations(job_id: int, session: Session = Depends(get_session)):
    associations = session.exec(
        select(FrameTranscriptAssociation)
        .join(VideoFrameTimeseries)
        .where(VideoFrameTimeseries.job_id == job_id)
    ).all()
    return associations