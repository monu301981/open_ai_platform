import os
import json
import subprocess
from fastapi import FastAPI, Depends, BackgroundTasks, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
from database import create_db_and_tables, get_session, engine
from models import AudioJob, AudioTranscriptChunk
from datetime import datetime
from transformers import pipeline
import torchaudio
from semantic_search import generate_transcript_embeddings, semantic_search
import torch

app = FastAPI()

class MediaRequest(BaseModel):
    file_name: str  # e.g., "example.mp4" or "example.mp3"
    duration: int | None = None  # Optional duration in seconds

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5

def check_ffmpeg():
    """Verify FFmpeg is installed and accessible."""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise RuntimeError("FFmpeg is not installed or not found in PATH. Install FFmpeg and add it to PATH.")

def check_audio_stream(file_path: str):
    """Check if the media file has an audio stream."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_streams", "-select_streams", "a", "-of", "json", file_path],
            capture_output=True, text=True, check=True
        )
        streams = json.loads(result.stdout).get("streams", [])
        return len(streams) > 0
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def extract_audio_from_video(video_path: str, audio_path: str):
    """Extract audio from video file using FFmpeg."""
    try:
        subprocess.run(
            ["ffmpeg", "-i", video_path, "-vn", "-acodec", "mp3", "-y", audio_path],
            capture_output=True, check=True
        )
    except subprocess.CalledProcessError as e:
        raise ValueError(f"Failed to extract audio from {video_path}: {e.stderr.decode()}")

@app.on_event("startup")
def on_startup():
    check_ffmpeg()  # Ensure FFmpeg is available on startup
    create_db_and_tables()
    os.makedirs("../contents/media", exist_ok=True)

@app.post("/process_media_audio/")
def process_media_audio(request: MediaRequest, background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
    file_name = request.file_name
    media_name = file_name.rsplit('.', 1)[0] if '.' in file_name else file_name
    media_path = os.path.join("..", "contents", "media", file_name)
    
    if not os.path.exists(media_path):
        raise HTTPException(status_code=404, detail=f"Media file not found: {media_path}")
    
    if not check_audio_stream(media_path):
        raise HTTPException(status_code=400, detail=f"No audio stream found in: {media_path}")

    job = AudioJob(file_name=file_name, media_name=media_name, status="pending")
    session.add(job)
    session.commit()
    session.refresh(job)
    background_tasks.add_task(process_audio, job.id, media_path, media_name, request.duration)
    return {"job_id": job.id, "file_name": file_name, "media_name": media_name}

def process_audio(job_id: int, media_path: str, media_name: str, provided_duration: int | None = None):
    with Session(engine) as session:
        job = session.get(AudioJob, job_id)
        job.status = "processing"
        session.commit()

        try:
            base_folder = os.path.join("..", "contents", "media", media_name)
            os.makedirs(base_folder, exist_ok=True)
            json_path = os.path.join(base_folder, "transcript_data.json")

            # Check if media is video (extract audio) or audio (use directly)
            file_ext = os.path.splitext(media_path)[1].lower()
            audio_path = media_path
            if file_ext in ['.mp4', '.avi', '.mov', '.mkv']:  # Video formats
                audio_path = os.path.join(base_folder, f"{media_name}.mp3")
                extract_audio_from_video(media_path, audio_path)

            # Load audio
            try:
                waveform, sample_rate = torchaudio.load(audio_path)
            except Exception as e:
                raise ValueError(f"Failed to load audio from {audio_path}: {str(e)}")

            if waveform.shape[0] > 1:  # Convert to mono if stereo
                waveform = waveform.mean(dim=0, keepdim=True)

            # Get total duration
            info = torchaudio.info(audio_path)
            total_duration = info.num_frames / info.sample_rate
            max_duration = provided_duration if provided_duration is not None else total_duration
            print(f"Processing media {media_path} with duration: {total_duration:.2f} seconds, max_duration: {max_duration:.2f} seconds")

            # Load Whisper model
            transcriber = pipeline("automatic-speech-recognition", model="openai/whisper-tiny", device=0 if torch.cuda.is_available() else -1)

            # Process audio in chunks (5 seconds each)
            chunk_duration = 5  # seconds
            sample_rate_hz = sample_rate
            chunk_samples = int(chunk_duration * sample_rate_hz)
            total_samples = waveform.shape[1]
            max_duration_samples = int(max_duration * sample_rate_hz)
            chunk_index = 0
            all_transcripts = []

            for start_sample in range(0, min(total_samples, max_duration_samples), chunk_samples):
                end_sample = min(start_sample + chunk_samples, total_samples)
                chunk_waveform = waveform[:, start_sample:end_sample]
                
                # Transcribe chunk
                try:
                    result = transcriber({"raw": chunk_waveform.squeeze().numpy(), "sampling_rate": sample_rate_hz})
                    transcript = result["text"] if result and "text" in result else ""
                except Exception as e:
                    print(f"Transcription failed for chunk {chunk_index}: {str(e)}")
                    transcript = ""

                # Save transcript chunk to DB
                start_time = start_sample / sample_rate_hz
                end_time = end_sample / sample_rate_hz
                chunk_record = AudioTranscriptChunk(
                    job_id=job.id,
                    chunk_index=chunk_index,
                    start_time=start_time,
                    end_time=end_time,
                    transcript=transcript
                )
                session.add(chunk_record)
                session.commit()

                # Save transcript info for JSON
                all_transcripts.append({
                    "chunk_index": chunk_index,
                    "start_time": start_time,
                    "end_time": end_time,
                    "transcript": transcript
                })
                chunk_index += 1

            # Generate embeddings for transcript chunks
            try:
                generate_transcript_embeddings(job_id, session)
            except Exception as e:
                print(f"Embedding generation failed: {str(e)}")

            # Save JSON file
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump({
                    "media_name": media_name,
                    "media_file": job.file_name,
                    "transcript_chunks": all_transcripts,
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
            print(f"Error processing media for job {job_id}: {e}")

@app.get("/job/{job_id}")
def get_job(job_id: int, session: Session = Depends(get_session)):
    job = session.get(AudioJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job

@app.get("/transcripts/{job_id}")
def get_transcripts(job_id: int, session: Session = Depends(get_session)):
    chunks = session.exec(select(AudioTranscriptChunk).where(AudioTranscriptChunk.job_id == job_id)).all()
    if not chunks:
        raise HTTPException(status_code=404, detail=f"No transcripts found for job {job_id}")
    return chunks

@app.get("/transcript-at-time/{job_id}/{timestamp}")
def get_transcript_at_time(job_id: int, timestamp: float, session: Session = Depends(get_session)):
    chunk = session.exec(
        select(AudioTranscriptChunk)
        .where(
            (AudioTranscriptChunk.job_id == job_id) &
            (AudioTranscriptChunk.start_time <= timestamp) &
            (AudioTranscriptChunk.end_time > timestamp)
        )
    ).first()
    if not chunk:
        raise HTTPException(status_code=404, detail=f"No transcript found for job {job_id} at timestamp {timestamp}")
    return chunk

@app.post("/search/{job_id}")
def search_transcripts(job_id: int, request: SearchRequest, session: Session = Depends(get_session)):
    results = semantic_search(request.query, job_id, request.top_k)
    return results