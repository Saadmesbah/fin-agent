from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer
from pathlib import Path
from datetime import datetime
from threading import RLock
import atexit

from rag.chunk import load_all

MODEL_NAME = "BAAI/bge-small-en-v1.5"
COLLECTION = "filings"
DB_PATH = str(Path(__file__).resolve().parents[1] / "data/qdrant")
BATCH = 64
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

_model = None
_client = None
_lock = RLock()


def get_client():
    global _client
    if _client is None:
        if not Path(DB_PATH, "meta.json").exists():
            raise FileNotFoundError("Build the filing index first: python -m rag.index")
        _client = QdrantClient(path=DB_PATH)
    return _client


def close_client():
    global _client
    with _lock:
        if _client is not None:
            _client.close()
            _client = None


atexit.register(close_client)


def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def build_index():
    chunks = load_all()
    if not chunks:
        raise ValueError("No extracted text found; run ingest.filings_to_text first")
    if len({(c['ticker'], c['chunk_id']) for c in chunks}) != len(chunks):
        raise ValueError("Duplicate chunk identifiers")
    model = get_model()
    close_client()
    # Preserve the prior index; do not depend on silently ignored Windows deletes.
    path = Path(DB_PATH)
    if path.exists():
        path.rename(path.with_name("qdrant_backup_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f")))
    client = QdrantClient(path=DB_PATH)
    client.create_collection(
        COLLECTION,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    )
    for i in range(0, len(chunks), BATCH):
        batch = chunks[i:i + BATCH]
        vecs = model.encode([c["text"] for c in batch], normalize_embeddings=True)
        points = [
            PointStruct(id=i + j, vector=v.tolist(), payload=c)
            for j, (c, v) in enumerate(zip(batch, vecs))
        ]
        client.upsert(COLLECTION, points)
        print(f"indexed {min(i + BATCH, len(chunks))}/{len(chunks)}")
    print("total in Qdrant:", client.count(COLLECTION).count)
    client.close()


def search(query: str, k: int = 5, ticker: str | None = None):
    if not query.strip() or not 1 <= k <= 100:
        raise ValueError("Provide a nonempty query and k between 1 and 100")
    with _lock:
        client = get_client()
        vec = get_model().encode(QUERY_PREFIX + query, normalize_embeddings=True).tolist()
        flt = None
        if ticker:
            flt = Filter(must=[FieldCondition(key="ticker", match=MatchValue(value=ticker.upper()))])
        res = client.query_points(COLLECTION, query=vec, limit=k, query_filter=flt).points
    return [{"score": r.score, **r.payload} for r in res]


if __name__ == "__main__":
    build_index()
    for r in search("What are Apple's main risk factors?", k=3, ticker="AAPL"):
        print(round(r["score"], 3), r["ticker"], r["chunk_id"], r["text"][:150].replace("\n", " "))
