from sqlmodel import Session, select
from database import engine
from models import AudioTranscriptChunk, AudioTranscriptVector
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict
import json

def generate_transcript_embeddings(job_id: int, session: Session) -> None:
    """
    Generate embeddings for all transcript chunks of a job and store in AudioTranscriptVector.
    """
    model = SentenceTransformer('all-MiniLM-L6-v2')
    chunks = session.exec(
        select(AudioTranscriptChunk).where(AudioTranscriptChunk.job_id == job_id)
    ).all()
    
    for chunk in chunks:
        # Skip empty transcripts
        if not chunk.transcript or chunk.transcript.strip() == "":
            continue
        embedding = model.encode(chunk.transcript).tolist()
        vector_record = AudioTranscriptVector(
            job_id=chunk.job_id,
            chunk_id=chunk.id,
            chunk_index=chunk.chunk_index,
            vector=json.dumps(embedding),
            transcript=chunk.transcript
        )
        session.add(vector_record)
    session.commit()

def semantic_search(query: str, job_id: int, top_k: int = 5) -> List[Dict]:
    """
    Perform semantic search over transcript chunks for a job using a query string.
    Returns the top_k most similar chunks with their metadata.
    """
    model = SentenceTransformer('all-MiniLM-L6-v2')
    query_embedding = model.encode(query)

    with Session(engine) as session:
        vectors = session.exec(
            select(AudioTranscriptVector).where(AudioTranscriptVector.job_id == job_id)
        ).all()
        
        if not vectors:
            return []

        # Compute cosine similarities
        results = []
        for vector in vectors:
            vector_array = np.array(json.loads(vector.vector))
            similarity = np.dot(query_embedding, vector_array) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(vector_array)
            )
            results.append({
                "chunk_id": vector.chunk_id,
                "chunk_index": vector.chunk_index,
                "transcript": vector.transcript,
                "similarity": float(similarity),
                "start_time": session.get(AudioTranscriptChunk, vector.chunk_id).start_time,
                "end_time": session.get(AudioTranscriptChunk, vector.chunk_id).end_time
            })

        # Sort by similarity and return top_k
        results = sorted(results, key=lambda x: x["similarity"], reverse=True)[:top_k]
        return results