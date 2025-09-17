# FastAPI Video Processing Service

## Overview

This service extracts frames and metadata from YouTube videos or local video files and stores:
- **Job metadata** (`VideoJob`)
- **Timeseries per-frame data** (`VideoFrameTimeseries`)
- **Vector embeddings for semantic search** (`VideoFrameVector`)
- **Audio transcription chunks** (`AudioTranscriptChunk`)
- **Associations between frames and transcript chunks** (timestamps or explicit links)

All data is stored in PostgreSQL using [SQLModel](https://sqlmodel.tiangolo.com/).

---

## Setup

### 1. Folder Structure and Virtual Environment (venv)

**Recommended structure:**
```
parent_folder/
│
├── contents/
│   └── media/
│       ├── <video_name>.mp4
│       └── <video_name>/
│           ├── frame_00000.jpg
│           ├── frame_00001.jpg
│           └── video_data.json
│
└── fastapi-video/
    ├── venv/
    ├── main.py
    ├── models.py
    ├── database.py
    ├── requirements.txt
    ├── README.md
    ├── REST_API_USAGE.md
    ├── urls.json
    └── video_config.json
```

FastAPI Audio Transcription Service
Overview

This service extracts audio from local media files (audio or video) in ../contents/media/, generates time-series transcripts using the Whisper speech-to-text model, and stores the results in a PostgreSQL database (Test2). For video files, it extracts audio to an MP3 file before transcription. It supports:

    Job metadata (AudioJob): Stores file name, media name, status, and results.
    Time-series transcript chunks (AudioTranscriptChunk): Stores transcripts with start/end times.
    Semantic embeddings (AudioTranscriptVector): For similarity search on transcripts.

Supported formats include audio (MP3, WAV, etc.) and video (MP4, AVI, etc.) files with audio streams. The service relies on FFmpeg for audio extraction. All data is stored in PostgreSQL using SQLModel.

**Recommended structure:**
```
audio_transcript_service/
│
├── venv/
├── main.py
├── models.py
├── database.py
├── semantic_search.py
├── requirements.txt
├── README.md
├── REST_API_USAGE.md
└── ../contents/
    └── media/
        ├── example.mp4  # Video or audio files
        ├── example.mp3
        └── example/
            ├── example.mp3  # Extracted audio for video files
            └── transcript_data.json
```
Installation
Follow the platform-specific instructions below to set up the project.

# AI Chat API for Rego Policy Evaluation

This project is a FastAPI-based REST API that allows users to query Rego policies (using Open Policy Agent, OPA) with a chat-like interface. It dynamically loads Rego policy and data files based on the product name specified in the query (e.g., `policies/<product>.rego` and `data/<product>.json`) and evaluates access permissions.

## Features
- Accepts chat-like queries (e.g., "Check access for product mediacomposer with region us, usage 1 TB, license Avid Platinum").
- Dynamically loads `<product>.rego` and `<product>.json` based on the product name.
- Supports flexible attribute querying (any key-value pairs in the query).
- Uploads policies to OPA via the `/v1/policies` endpoint with retry logic.
- Evaluates queries against the specified Rego policy using OPA.
- Combines user input with data from the product's JSON file.
- Returns whether access is allowed based on the policy.
- Separate service for Rego handling (`rego_service.py`).

