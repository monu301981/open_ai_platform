import os
import ssl
import urllib
import requests
import cv2
import json
import shutil
from ultralytics import YOLO
from transformers import BlipProcessor, BlipForConditionalGeneration
from sentence_transformers import SentenceTransformer
import torch
from PIL import Image
from yt_dlp import YoutubeDL
from database import get_session, engine
from models import VideoFrameTimeseries, VideoFrameVector, AudioTranscriptChunk, FrameTranscriptAssociation
from sqlmodel import Session, select

def get_video_id_from_url(url):
    if not url:
        return None
    import re
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

def process_video(youtube_url: str | None, local_path: str | None, output_folder: str, job_id: int) -> str:
    if not youtube_url and not local_path:
        raise ValueError("Either youtube_url or local_path must be provided")
    
    # Prepare paths
    video_name = os.path.basename(output_folder)
    video_path = os.path.join("../contents/media", f"{video_name}.mp4")
    os.makedirs(output_folder, exist_ok=True)

    # Handle video source
    if local_path:
        if not os.path.exists(local_path):
            raise ValueError("Local file does not exist")
        if not local_path.lower().endswith(('.mp4', '.avi', '.mkv')):
            raise ValueError("Unsupported video format")
        cap = cv2.VideoCapture(local_path)
        if not cap.isOpened():
            raise ValueError("Error: Could not open local video file")
        cap.release()
        shutil.copy(local_path, video_path)
        duration = get_video_duration(local_path=local_path)
    else:
        requests.get(
            'https://huggingface.co/api/models/Salesforce/blip-image-captioning-base/revision/main',
            verify=False
        )
        os.environ['CURL_CA_BUNDLE'] = ''
        ssl._create_default_https_context = ssl._create_unverified_context
        urllib.request.urlopen("https://www.youtube.com")
        duration = get_video_duration(youtube_url)
        section_str = f"*00:00-00:{duration:02d}"
        ydl_opts = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
            "outtmpl": video_path,
            "quiet": False,
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
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError("Error: Could not open video.")
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = 0
    data = []
    chunk_size = int(fps * 5) if fps > 0 else 25
    chunk_captions = []
    all_transcripts = []
    max_duration = float(duration)

    # DB session
    session = Session(engine)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        timestamp = frame_count / fps if fps > 0 else frame_count / 25
        if timestamp > max_duration:
            break

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        yolo_results = yolo_model(frame_rgb)
        objects = [(int(box.cls), float(box.conf)) for box in yolo_results[0].boxes]
        object_names = [f"{yolo_model.names[obj]} ({conf:.2f})" for obj, conf in objects]

        pil_img = Image.fromarray(frame_rgb)
        inputs = processor(pil_img, return_tensors="pt").to(device)
        with torch.no_grad():
            output_ids = blip_model.generate(**inputs, max_length=50)
            caption = processor.decode(output_ids[0], skip_special_tokens=True)

        annotated_frame = yolo_results[0].plot()
        image_filename = f"frame_{frame_count:05d}.jpg"
        image_path = os.path.join(output_folder, image_filename)
        cv2.imwrite(image_path, annotated_frame)

        # Store timeseries data
        ts_row = VideoFrameTimeseries(
            job_id=job_id,
            frame_number=frame_count,
            timestamp=timestamp,
            image_file=image_filename,
            objects=json.dumps(object_names),
            caption=caption,
        )
        session.add(ts_row)
        session.flush()

        # Store vector data
        embedding = embed_model.encode(caption).tolist()
        vec_row = VideoFrameVector(
            job_id=job_id,
            timeseries_id=ts_row.id,
            frame_number=frame_count,
            vector=json.dumps(embedding),
            caption=caption,
        )
        session.add(vec_row)
        session.flush()

        data.append({
            "frame_number": frame_count,
            "timestamp": timestamp,
            "image_file": image_filename,
            "objects": object_names,
            "caption": caption,
            "vector_id": vec_row.id,
            "timeseries_id": ts_row.id,
        })

        chunk_captions.append(caption)
        if (frame_count + 1) % chunk_size == 0:
            transcript = " ".join(chunk_captions)
            start_time = (frame_count - chunk_size + 1) / fps if fps > 0 else (frame_count - chunk_size + 1) / 25
            end_time = frame_count / fps if fps > 0 else frame_count / 25
            chunk_record = AudioTranscriptChunk(
                job_id=job_id,
                chunk_index=len(all_transcripts),
                start_time=start_time,
                end_time=end_time,
                transcript=transcript
            )
            session.add(chunk_record)
            session.flush()

            # Create FrameTranscriptAssociation
            chunk_frames = session.exec(
                select(VideoFrameTimeseries)
                .where(
                    (VideoFrameTimeseries.job_id == job_id) &
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

            all_transcripts.append({
                "chunk_index": len(all_transcripts),
                "start_frame": frame_count - chunk_size + 1,
                "end_frame": frame_count,
                "transcript": transcript
            })
            chunk_captions = []

        frame_count += 1

    if chunk_captions:
        transcript = " ".join(chunk_captions)
        start_time = (frame_count - len(chunk_captions)) / fps if fps > 0 else (frame_count - len(chunk_captions)) / 25
        end_time = frame_count / fps if fps > 0 else frame_count / 25
        chunk_record = AudioTranscriptChunk(
            job_id=job_id,
            chunk_index=len(all_transcripts),
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
                (VideoFrameTimeseries.job_id == job_id) &
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

        all_transcripts.append({
            "chunk_index": len(all_transcripts),
            "start_frame": frame_count - len(chunk_captions),
            "end_frame": frame_count - 1,
            "transcript": transcript
        })

    cap.release()
    session.commit()
    session.close()

    metadata = {
        "video_url": youtube_url,
        "local_path": local_path,
        "video_path": video_path,
        "frames": data,
        "transcripts": all_transcripts,
        "fps": fps,
        "frame_count": frame_count,
        "extracted_duration_seconds": duration
    }
    json_path = os.path.join(output_folder, "video_data.json")
    with open(json_path, "w") as f:
        json.dump(metadata, f, indent=2)

    return json_path