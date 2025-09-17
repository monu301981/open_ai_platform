# FastAPI Audio Transcription Service

## Overview

This service extracts audio from local media files (audio or video) in `../contents/media/`, generates time-series transcripts using the Whisper speech-to-text model, and stores the results in a PostgreSQL database (`Test2`). For video files, it extracts audio to an MP3 file before transcription. It supports:
- **Job metadata** (`AudioJob`): Stores file name, media name, status, and results.
- **Time-series transcript chunks** (`AudioTranscriptChunk`): Stores transcripts with start/end times.
- **Semantic embeddings** (`AudioTranscriptVector`): For similarity search on transcripts.

Supported formats include audio (MP3, WAV, etc.) and video (MP4, AVI, etc.) files with audio streams. The service relies on FFmpeg for audio extraction. All data is stored in PostgreSQL using [SQLModel](https://sqlmodel.tiangolo.com/).

## Project Structure

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

## Installation

Follow the platform-specific instructions below to set up the project.

### Windows

1. **Create Project Directory**
   ```sh
   mkdir audio_transcript_service
   cd audio_transcript_service
   ```

2. **Create and Activate Virtual Environment**
   ```sh
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Upgrade pip**
   ```sh
   venv\Scripts\python.exe -m pip install --upgrade pip
   ```

4. **Install FFmpeg**
   - Download FFmpeg from [https://www.gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/) (e.g., `ffmpeg-release-essentials.zip`).
   - Extract the zip to a folder (e.g., `C:\ffmpeg`).
   - Add FFmpeg to the system PATH:
     - Right-click "This PC" > Properties > Advanced system settings > Environment Variables.
     - Under "System variables," find `Path`, click Edit, and add `C:\ffmpeg\bin` (adjust path if different).
   - Verify FFmpeg installation:
     ```sh
     ffmpeg -version
     ```

5. **Install Python Dependencies**
   ```sh
   pip install -r requirements.txt
   ```

6. **Set up PostgreSQL**
   - Install PostgreSQL (e.g., from [https://www.postgresql.org/download/windows/](https://www.postgresql.org/download/windows/)).
   - Start the PostgreSQL server (use pgAdmin or command line).
   - Create the `Test2` database:
     ```sh
     psql -U postgres -c "CREATE DATABASE Test2;"
     ```
   - Ensure the database URL in `database.py` matches:
     ```
     postgresql+psycopg2://postgres:admin@localhost:5432/Test2
     ```
     Update the username/password if different.

7. **Prepare Media Files**
   - Place audio (e.g., `example.mp3`) or video (e.g., `example.mp4`) files in `../contents/media/`.
   - Create the folder if needed:
     ```sh
     mkdir ..\contents\media
     ```
   - Ensure files have audio (verify with `ffprobe ../contents/media/example.mp4`).

8. **Run the Server**
   ```sh
   uvicorn main:app --reload
   ```

### Linux (Ubuntu/Debian)

1. **Create Project Directory**
   ```sh
   mkdir audio_transcript_service
   cd audio_transcript_service
   ```

2. **Create and Activate Virtual Environment**
   ```sh
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Upgrade pip**
   ```sh
   venv/bin/python -m pip install --upgrade pip
   ```

4. **Install FFmpeg**
   ```sh
   sudo apt update
   sudo apt install ffmpeg
   ```
   - Verify installation:
     ```sh
     ffmpeg -version
     ```

5. **Install Python Dependencies**
   ```sh
   pip install -r requirements.txt
   ```

6. **Set up PostgreSQL**
   - Install PostgreSQL:
     ```sh
     sudo apt install postgresql postgresql-contrib
     ```
   - Start the PostgreSQL service:
     ```sh
     sudo service postgresql start
     ```
   - Create the `Test2` database:
     ```sh
     psql -U postgres -c "CREATE DATABASE Test2;"
     ```
   - Ensure the database URL in `database.py` matches:
     ```
     postgresql+psycopg2://postgres:admin@localhost:5432/Test2
     ```

7. **Prepare Media Files**
   - Place audio (e.g., `example.mp3`) or video (e.g., `example.mp4`) files in `../contents/media/`.
   - Create the folder if needed:
     ```sh
     mkdir -p ../contents/media
     ```
   - Ensure files have audio (verify with `ffprobe ../contents/media/example.mp4`).

8. **Run the Server**
   ```sh
   uvicorn main:app --reload
   ```

### macOS

1. **Create Project Directory**
   ```sh
   mkdir audio_transcript_service
   cd audio_transcript_service
   ```

2. **Create and Activate Virtual Environment**
   ```sh
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Upgrade pip**
   ```sh
   venv/bin/python -m pip install --upgrade pip
   ```

4. **Install FFmpeg**
   - Install Homebrew if not already installed:
     ```sh
     /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
     ```
   - Install FFmpeg:
     ```sh
     brew install ffmpeg
     ```
   - Verify installation:
     ```sh
     ffmpeg -version
     ```

5. **Install Python Dependencies**
   ```sh
   pip install -r requirements.txt
   ```

6. **Set up PostgreSQL**
   - Install PostgreSQL using Homebrew:
     ```sh
     brew install postgresql
     ```
   - Start the PostgreSQL service:
     ```sh
     brew services start postgresql
     ```
   - Create the `Test2` database:
     ```sh
     psql -U postgres -c "CREATE DATABASE Test2;"
     ```
   - Ensure the database URL in `database.py` matches:
     ```
     postgresql+psycopg2://postgres:admin@localhost:5432/Test2
     ```

7. **Prepare Media Files**
   - Place audio (e.g., `example.mp3`) or video (e.g., `example.mp4`) files in `../contents/media/`.
   - Create the folder if needed:
     ```sh
     mkdir -p ../contents/media
     ```
   - Ensure files have audio (verify with `ffprobe ../contents/media/example.mp4`).

8. **Run the Server**
   ```sh
   uvicorn main:app --reload
   ```

## Testing the Application

1. **Place a Media File**
   - Copy a valid audio (e.g., `example.mp3`) or video file (e.g., `example.mp4`) to `../contents/media/`.
   - Ensure it has an audio stream:
     ```sh
     ffprobe -v error -show_streams -select_streams a ../contents/media/example.mp3
     ```

2. **Submit a Job**
   ```sh
   curl -X POST "http://localhost:8000/process_media_audio/" -H "Content-Type: application/json" -d '{"file_name": "example.mp3"}'
   ```

3. **Check Job Status**
   ```sh
   curl http://localhost:8000/job/1
   ```

4. **Retrieve Transcripts**
   ```sh
   curl http://localhost:8000/transcripts/1
   ```

5. **Perform Semantic Search**
   ```sh
   curl -X POST "http://localhost:8000/search/1" -H "Content-Type: application/json" -d '{"query": "example term", "top_k": 3}'
   ```

6. **Verify Output**
   - Check JSON: `../contents/media/<media_name>/transcript_data.json`.
   - Check extracted audio (for video files): `../contents/media/<media_name>/<media_name>.mp3`.
   - Query database:
     ```sql
     SELECT * FROM audiojob;
     SELECT * FROM audiotranscriptchunk WHERE job_id = 1;
     SELECT * FROM audiotranscriptvector WHERE job_id = 1;
     ```

## REST API Usage
See [REST_API_USAGE.md](./REST_API_USAGE.md) for endpoint documentation.

## Notes
- Always activate the virtual environment before running or installing.
- Tables are auto-created on startup.
- Media files must be in `../contents/media/` and have audio streams.
- FFmpeg is required for audio extraction.

## Troubleshooting

- **FFmpeg Errors**:
  - If `ffmpeg -version` fails, ensure FFmpeg is installed and in PATH.
  - Windows: Add `C:\ffmpeg\bin` to PATH and restart your terminal.
  - Linux/macOS: Reinstall FFmpeg (`sudo apt install ffmpeg` or `brew install ffmpeg`).

- **ModuleNotFoundError**:
  - Ensure dependencies are installed in the active virtual environment:
    ```sh
    pip install -r requirements.txt
    ```

- **Database Errors**:
  - Verify PostgreSQL is running and `Test2` exists.
  - Check `database.py` for correct username/password.

- **Media File Errors**:
  - Ensure the file exists in `../contents/media/` and has audio (use `ffprobe`).
  - Convert unsupported formats to MP3 or MP4:
    ```sh
    ffmpeg -i input_file -c:a mp3 output.mp3  # For audio
    ffmpeg -i input_file -c:v copy -c:a aac output.mp4  # For video
    ```

- **Whisper Model Issues**:
  - Use `openai/whisper-tiny` for low resource usage. Upgrade to `openai/whisper-small` for better accuracy if resources allow.

## License
MIT