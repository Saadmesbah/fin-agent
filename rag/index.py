from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer

from rag.chunk import load_all

MODEL_NAME = "BAAI/bge-small-en-v1.5"
COLLECTION = "filings"
DB_PATH = "data/qdrant"
BATCH = 64
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

_model = None


def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def build_index():
    chunks = load_all()
    model = get_model()
    client = QdrantClient(path=DB_PATH)
    if client.collection_exists(COLLECTION):
        client.delete_collection(COLLECTION)
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
    client = QdrantClient(path=DB_PATH)
    vec = get_model().encode(QUERY_PREFIX + query, normalize_embeddings=True).tolist()
    flt = None
    if ticker:
        flt = Filter(must=[FieldCondition(key="ticker", match=MatchValue(value=ticker))])
    res = client.query_points(COLLECTION, query=vec, limit=k, query_filter=flt).points
    client.close()
    return [{"score": r.score, **r.payload} for r in res]


if __name__ == "__main__":
    build_index()
    for r in search("What are Apple's main risk factors?", k=3, ticker="AAPL"):
        print(round(r["score"], 3), r["ticker"], r["chunk_id"], r["text"][:150].replace("\n", " "))