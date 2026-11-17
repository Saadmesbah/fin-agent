import pytest
import yaml

from eval.eval_retrieval import evidence_matches, load_questions
from rag.retrieve import fuse


def test_phrase_alternatives():
    assert evidence_matches("Our AI models may be flawed", ["artificial intelligence", "AI models"])
    assert evidence_matches("SUPPLY\n  chain", "supply chain")
    assert not evidence_matches("iPhone | 123", "iPhone | 209,586")


@pytest.mark.parametrize("evidence", [None, "", [], [""], [123], 17])
def test_invalid_evidence_is_rejected(tmp_path, evidence):
    path = tmp_path / "benchmark.yaml"
    path.write_text(yaml.safe_dump([{"id": "r1", "type": "docs", "question": "q",
                                     "company": "MSFT", "expected_evidence": evidence}]), encoding="utf-8")
    with pytest.raises(ValueError):
        load_questions(path)


def test_fusion_rewards_independent_agreement():
    a = {"ticker": "AAPL", "chunk_id": 0, "text": "a"}
    b = {"ticker": "AAPL", "chunk_id": 1, "text": "b"}
    result = fuse([[a, b], [b]], 2)
    assert [c["chunk_id"] for c in result] == [1, 0]


def test_local_qdrant_reopen_and_filter(tmp_path):
    from qdrant_client import QdrantClient, models
    path = str(tmp_path / "qdrant")
    client = QdrantClient(path=path)
    try:
        client.create_collection("filings", vectors_config=models.VectorParams(size=2, distance=models.Distance.COSINE))
        client.upsert("filings", [models.PointStruct(id=0, vector=[1., 0.], payload={"ticker": "MSFT"}),
                                  models.PointStruct(id=1, vector=[1., 0.], payload={"ticker": "AAPL"})])
    finally:
        client.close()
    client = QdrantClient(path=path)
    try:
        assert client.count("filings").count == 2
        result = client.query_points("filings", query=[1., 0.], query_filter=models.Filter(
            must=[models.FieldCondition(key="ticker", match=models.MatchValue(value="MSFT"))])).points
        assert [p.id for p in result] == [0]
    finally:
        client.close()
