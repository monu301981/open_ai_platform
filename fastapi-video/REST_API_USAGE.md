# REST API Usage Guide

## FastAPI Video Processing Service

This guide documents all available endpoints.

---

## Endpoints

### 1. Process a Video (YouTube URL or Local File)

**POST /process_media_video/**  
Processes a YouTube URL or a local video file, expects JSON:

**Request**
```json
{ "url": "https://www.youtube.com/watch?v=tPEE9ZwTmy0" }
```
OR
```json
{ "local_path": "/path/to/video.mp4" }
```
**Notes**:
- Provide exactly one of `url` or `local_path`.
- Supported local file formats: .mp4, .avi, .mkv.
- Local file must exist and be accessible.

**Response**
```json
{ 
  "job_id": 1, 
  "url": "https://www.youtube.com/watch?v=xyz", 
  "local_path": null, 
  "video_name": "xyz" 
}
```

---

### 2. Get Job Status/Results

**GET /job/{job_id}**

Returns job metadata, status, error messages, and result JSON path.

---

### 3. Get Per-Frame Timeseries Data (for a job)

**GET /frames/{job_id}**

Returns all frames and their timeseries metadata for a given job.

---

### 4. Get Vector Embeddings for Semantic Search (for a job)

**GET /vectors/{job_id}**

Returns all frame-level vector embeddings and their metadata for a given job.

---

### 5. Get Both Vector and Timeseries for a Frame

**GET /frame-vector/{frame_id}**

Returns both the vector embedding and corresponding timeseries data for a single frame.

---

### 6. Get Transcript Chunks for a Job

**GET /transcripts/{job_id}**

Returns all audio transcript chunks for a job.

---

### 7. Get Frames for a Transcript Chunk

**GET /frames-for-transcript/{chunk_id}**

Returns all frames whose timestamps fall within a transcript chunk's time window.

---

### 8. Get Transcript Chunk for a Frame

**GET /transcript-for-frame/{frame_id}**

Returns the transcript chunk covering the frame's timestamp.

---

## Data Model Summary

- **VideoJob**: Job metadata and result status.
- **VideoFrameTimeseries**: Per-frame time-indexed data (objects, captions, timestamps).
- **VideoFrameVector**: Per-frame vector embeddings for semantic search.
- **AudioTranscriptChunk**: Time-windowed transcript data for semantic/audio search.

---

## Example Workflow

1. **Submit video processing job:**  
   - POST `/process_media_video/` with a YouTube URL or local file path.
2. **Check job status:**  
   - GET `/job/{job_id}`
3. **Get extracted frame data:**  
   - GET `/frames/{job_id}` for timeseries
   - GET `/vectors/{job_id}` for vectors
   - GET `/transcripts/{job_id}` for transcripts
4. **Joint analytics:**  
   - GET `/frames-for-transcript/{chunk_id}` or `/transcript-for-frame/{frame_id}`

---

## Extending

- Add endpoints for semantic or transcript-based search, filtering, or analytics.
- Integrate pgvector for fast similarity search or sync to a dedicated vector DB for large-scale workloads.

---

## Notes

- All tables are auto-created on startup.
- Data is stored in PostgreSQL; you may extend with pgvector or other DBs as needed.
- Local video files are copied to the `../contents/media/` folder for processing.