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

### 2. Create and Activate Virtual Environment

**Windows:**
```sh
python -m venv venv
venv\Scripts\activate
```
**Linux/macOS:**
```sh
python3 -m venv venv
source venv/bin/activate
```

### 3. Upgrade pip (if needed)
```sh
venv\Scripts\python.exe -m pip install --upgrade pip       # Windows
venv/bin/python -m pip install --upgrade pip               # Linux/macOS
```

### 4. Install dependencies

```sh
pip install -r requirements.txt
```

### 5. Set up PostgreSQL

- Make sure your database is running at:
  ```
  postgresql+psycopg2://postgres:admin@localhost:5432/Test1
  ```
- Create the `Test1` database if it doesn't exist.

### 6. Configure video extraction duration

- Edit `video_config.json` to set per-video duration.
- The `"default"` key sets fallback duration (e.g. 20 seconds).

### 7. Run the server

```sh
uvicorn main:app --reload
```

---

## REST API Usage

See [REST_API_USAGE.md](./REST_API_USAGE.md) for endpoint documentation and examples.

---

## Notes

- Always activate your `venv` before running/installing anything.
- All extracted data is stored for semantic, timeseries, and transcript chunk search.
- Tables are auto-created on startup.
- Frame images are stored in `../contents/media/<video_name>/`.

---

## Troubleshooting

If you see `ModuleNotFoundError: No module named 'sentence_transformers'`, install dependencies after activating your venv:

```sh
pip install -r requirements.txt
```

If you see an error about upgrading pip, run:
```sh
venv\Scripts\python.exe -m pip install --upgrade pip       # Windows
venv/bin/python -m pip install --upgrade pip               # Linux/macOS
```

---

## License

MIT
