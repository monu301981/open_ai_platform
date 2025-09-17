# REST API Usage Guide

## FastAPI Audio Transcription Service

This guide documents the available endpoints for processing local media files (audio or video) and retrieving transcripts.

## Endpoints

### 1. Process a Local Media File
**POST /process_media_audio/**  
Submits a media file (audio or video) from `../contents/media/` for audio extraction and transcription. For video files, an MP3 audio file is extracted before transcription. The file must be in `../contents/media/` and have an audio stream.

**Request:**
```json
{ "file_name": "example.mp3", "duration": 20 }
```
- `file_name`: Name of the audio (e.g., `example.mp3`) or video (e.g., `example.mp4`) file.
- `duration`: Optional; if omitted, the full file is processed.

**Response:**
```json
{ "job_id": 1, "file_name": "example.mp3", "media_name": "example" }
```

### 2. Get Job Status/Results
**GET /job/{job_id}**  
Returns job metadata, status, error messages, and result JSON path.

### 3. Get Transcript Chunks
**GET /transcripts/{job_id}**  
Returns all transcript chunks for a given job.

### 4. Get Transcript at Timestamp
**GET /transcript-at-time/{job_id}/{timestamp}**  
Returns the transcript chunk covering the specified timestamp.

### 5. Semantic Search on Transcripts
**POST /search/{job_id}**  
Searches transcript chunks for a job using a query string and returns the top matching chunks based on semantic similarity.

**Request:**
```json
{ "query": "example search term", "top_k": 5 }
```

**Response:**
```json
[
  {
    "chunk_id": 1,
    "chunk_index": 0,
    "transcript": "This is an example transcript",
    "similarity": 0.95,
    "start_time": 0.0,
    "end_time": 5.0
  },
  ...
]
```

## Data Model Summary
- **AudioJob**: Stores job metadata (file name, media name, status, result JSON path).
- **AudioTranscriptChunk**: Stores time-series transcript data (chunk index, start/end times, transcript text).
- **AudioTranscriptVector**: Stores semantic embeddings for transcript chunks for similarity search.

## Example Workflow
1. Place an audio or video file in `../contents/media/` (e.g., `example.mp3` or `example.mp4`).
2. Submit a processing job:
   ```sh
   curl -X POST "http://localhost:8000/process_media_audio/" -H "Content-Type: application/json" -d '{"file_name": "example.mp3", "duration": 20}'
   ```
3. Check job status:
   ```sh
   curl http://localhost:8000/job/1
   ```
4. Retrieve transcripts:
   ```sh
   curl http://localhost:8000/transcripts/1
   ```
5. Find transcript at a specific time:
   ```sh
   curl http://localhost:8000/transcript-at-time/1/10.5
   ```
6. Perform semantic search:
   ```sh
   curl -X POST "http://localhost:8000/search/1" -H "Content-Type: application/json" -d '{"query": "example term", "top_k": 3}'
   ```

## Extending
- Integrate `pgvector` for faster vector similarity search.
- Add filtering options for search results (e.g., time range).
- Support file uploads via API.

## Notes
- Tables are auto-created on startup.
- Data is stored in PostgreSQL; extend with vector databases if needed.
- Supported formats: MP3, WAV, MP4, AVI, etc. (any format FFmpeg supports).