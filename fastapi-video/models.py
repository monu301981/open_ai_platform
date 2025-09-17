from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime

class VideoJob(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    video_name: str
    url: str
    status: str = "pending"
    result_json_path: Optional[str] = None
    error_msg: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: Optional[datetime] = Field(default=None, nullable=True)

    frames: List["VideoFrameTimeseries"] = Relationship(back_populates="job")
    transcript_chunks: List["AudioTranscriptChunk"] = Relationship(back_populates="job")

class VideoFrameTimeseries(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="videojob.id")
    frame_number: int
    timestamp: float
    image_file: str
    objects: str
    caption: str

    job: Optional[VideoJob] = Relationship(back_populates="frames")
    vectors: List["VideoFrameVector"] = Relationship(back_populates="timeseries")

class VideoFrameVector(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="videojob.id")
    timeseries_id: int = Field(foreign_key="videoframetimeseries.id")
    frame_number: int
    vector: str
    caption: str

    timeseries: Optional[VideoFrameTimeseries] = Relationship(back_populates="vectors")

class AudioTranscriptChunk(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="videojob.id")
    chunk_index: int
    start_time: float
    end_time: float
    transcript: str

    job: Optional[VideoJob] = Relationship(back_populates="transcript_chunks")

class FrameTranscriptAssociation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    frame_id: int = Field(foreign_key="videoframetimeseries.id")
    transcript_chunk_id: int = Field(foreign_key="audiotranscriptchunk.id")