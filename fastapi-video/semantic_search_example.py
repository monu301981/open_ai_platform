from sentence_transformers import SentenceTransformer
from sqlmodel import Session, select
from models import VideoFrameVector

def semantic_search(query_text, top_n=5):
    embed_model = SentenceTransformer('all-MiniLM-L6-v2')
    query_vec = embed_model.encode(query_text).tolist()
    session = Session(engine)
    # Brute-force cosine similarity for demo; use pgvector for fast search
    results = []
    vectors = session.exec(select(VideoFrameVector)).all()
    import numpy as np
    def cosine(a, b):
        a, b = np.array(a), np.array(b)
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    for v in vectors:
        v_vec = json.loads(v.vector)
        score = cosine(query_vec, v_vec)
        results.append((score, v))
    results = sorted(results, key=lambda x: -x[0])[:top_n]
    session.close()
    return [{"vector_id": v.id, "caption": v.caption, "score": score} for score, v in results]