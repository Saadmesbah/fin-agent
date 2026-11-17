"""BM25 + vector reciprocal-rank fusion, with optional cross-encoder reranking."""
import re
from functools import lru_cache
from threading import RLock

from rank_bm25 import BM25Okapi

from rag.index import COLLECTION, _lock, get_client, search

_rerank_lock = RLock()


def tokens(text):
    return re.findall(r"\w+", text.casefold())


@lru_cache(maxsize=12)
def corpus(ticker):
    with _lock:
        client = get_client()
        points, offset = [], None
        while True:
            batch, offset = client.scroll(COLLECTION, offset=offset, limit=256, with_vectors=False)
            points.extend(batch)
            if offset is None:
                break
    chunks = [p.payload for p in points if not ticker or p.payload["ticker"] == ticker]
    if not chunks:
        raise ValueError(f"No document coverage for {ticker or 'this query'}")
    return chunks, BM25Okapi([tokens(c["text"]) for c in chunks])


def fuse(rankings, limit):
    scores, chunks = {}, {}
    for ranking in rankings:
        seen = set()
        for rank, chunk in enumerate(ranking, 1):
            key = (chunk["ticker"], chunk["chunk_id"])
            if key in seen:
                raise ValueError("Duplicate chunk in a retrieval ranking")
            seen.add(key)
            scores[key] = scores.get(key, 0) + 1 / (60 + rank)
            chunks[key] = chunk
    keys = sorted(scores, key=lambda key: (-scores[key], key))[:limit]
    return [{**chunks[key], "score": scores[key]} for key in keys]


@lru_cache(maxsize=1)
def reranker():
    from sentence_transformers import CrossEncoder
    return CrossEncoder("cross-encoder/ms-marco-MiniLM-L6-v2")


def retrieve(query, k=5, ticker=None, mode="vector"):
    if mode not in {"vector", "hybrid", "rerank"}:
        raise ValueError("Retrieval mode must be vector, hybrid, or rerank")
    if not 1 <= k <= 20:
        raise ValueError("k must be between 1 and 20")
    ticker = ticker.upper() if ticker else None
    if mode == "vector":
        return search(query, k=k, ticker=ticker)
    candidate_k = max(20, k)
    dense = search(query, k=candidate_k, ticker=ticker)
    chunks, bm25 = corpus(ticker)
    lexical_scores = bm25.get_scores(tokens(query))
    order = sorted(range(len(chunks)), key=lambda i: (-lexical_scores[i], i))
    lexical = [chunks[i] for i in order[:candidate_k] if lexical_scores[i] > 0]
    candidates = fuse([dense, lexical], candidate_k)
    if mode == "rerank":
        with _rerank_lock:
            scores = reranker().predict([(query, c["text"]) for c in candidates])
        candidates = sorted(
            [{**c, "score": float(s)} for c, s in zip(candidates, scores)],
            key=lambda c: (-c["score"], c["ticker"], c["chunk_id"]),
        )
    return candidates[:k]
