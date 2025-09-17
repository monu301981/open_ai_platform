from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
import json

class AudioJob(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    file_name: str  # e.g., "example.mp3" or "example.mp4"
    media_name: str  # e.g., "example"
    status: str = "pending"
    result_json_path: Optional[str] = None
    error_msg: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: Optional[datetime] = Field(default=None, nullable=True)

    transcript_chunks: List["AudioTranscriptChunk"] = Relationship(back_populates="job")
    transcript_vectors: List["AudioTranscriptVector"] = Relationship(back_populates="job")

class AudioTranscriptChunk(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="audiojob.id")
    chunk_index: int
    start_time: float
    end_time: float
    transcript: str

    job: Optional[AudioJob] = Relationship(back_populates="transcript_chunks")
    vectors: List["AudioTranscriptVector"] = Relationship(back_populates="chunk")

class AudioTranscriptVector(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="audiojob.id")
    chunk_id: int = Field(foreign_key="audiotranscriptchunk.id")
    chunk_index: int
    vector: str  # JSON-encoded embedding
    transcript: str

    job: Optional[AudioJob] = Relationship(back_populates="transcript_vectors")
    chunk: Optional[AudioTranscriptChunk] = Relationship(back_populates="vectors")