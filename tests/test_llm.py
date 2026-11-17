import pytest

from agent import llm


def test_transport_error_does_not_expose_key(monkeypatch):
    monkeypatch.setattr(llm, "load_dotenv", lambda *a, **k: None)
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-secret-never-print")
    monkeypatch.setenv("OPENROUTER_MODEL", "test/model")
    class Response:
        ok = False
        status_code = 429
    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: Response())
    with pytest.raises(RuntimeError, match="429") as exc:
        llm.complete("system", "question")
    assert "fake-secret" not in str(exc.value)


@pytest.mark.parametrize("text", ["not json", "[]", "null"])
def test_invalid_structured_output(text):
    with pytest.raises(ValueError):
        llm.parse_json(text)


def test_fenced_json():
    assert llm.parse_json('```json\n{"route":"sql"}\n```') == {"route": "sql"}
