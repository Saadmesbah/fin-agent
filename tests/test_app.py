import pytest
from fastapi.testclient import TestClient

import agent.graph as graph
import rag.answer as rag
from app.main import app


@pytest.mark.parametrize("text", ["Unsupported [MSFT:99]", "No citations here"])
def test_citation_validation(monkeypatch, text):
    monkeypatch.setattr(rag, "retrieve", lambda *a, **k: [
        {"ticker": "MSFT", "chunk_id": 11, "text": "Evidence", "score": 0.7}])
    monkeypatch.setattr(rag, "complete", lambda *a, **k: {"text": text, "model": "test", "usage": {}})
    with pytest.raises(RuntimeError):
        rag.answer("Question", "MSFT")


@pytest.mark.parametrize("route", ["sql", "rag", "both"])
def test_graph_routes_and_combines(monkeypatch, route):
    graph.get_graph.cache_clear()
    monkeypatch.setattr(graph, "run_sql", lambda state: {"sql_result": {"answer": "123", "sources": [{"label": "DuckDB"}]}})
    monkeypatch.setattr(graph, "run_rag", lambda state: {"rag_result": {"answer": "Facts [MSFT:11]", "sources": [{"label": "[MSFT:11]"}]}})
    result = graph.ask("Microsoft question", route=route)
    assert ("sql_result" in result) == (route in {"sql", "both"})
    assert ("rag_result" in result) == (route in {"rag", "both"})
    assert result["ticker"] == "MSFT"
    assert len(result["sources"]) == (2 if route == "both" else 1)
    graph.get_graph.cache_clear()


def test_auto_classifier_validation(monkeypatch):
    monkeypatch.setattr(graph, "complete", lambda *a, **k: {"text": '{"route":"delete"}'})
    with pytest.raises(ValueError):
        graph.route_question({"question": "Delete data"})


def test_no_documents_for_unsupported_company():
    with pytest.raises(ValueError, match="Documents"):
        graph.route_question({"question": "NVIDIA risks", "route": "rag"})


def test_api_health_validation_and_error(monkeypatch):
    import app.main as api
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/").status_code == 200
        assert client.post("/ask", json={"question": ""}).status_code == 422
        def fail(*args):
            raise ValueError("Bad route")
        monkeypatch.setattr(api, "ask", fail)
        assert client.post("/ask", json={"question": "q"}).status_code == 422
        monkeypatch.setattr(api, "ask", lambda *a: {"answer": "ok", "sources": [], "route": "sql"})
        assert client.post("/ask", json={"question": "q"}).json()["answer"] == "ok"
