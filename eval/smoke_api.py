"""Live end-to-end checks through FastAPI and the actual LangGraph/OpenRouter path."""
import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


if __name__ == "__main__":
    cases = [
        {"question": "What was Apple's revenue in 2023?", "expected_route": "sql"},
        {"question": "What are Microsoft's reportable segments?", "expected_route": "rag"},
        {"question": "What was Apple's revenue in 2023 and what manufacturing outsourcing risks does Apple describe?",
         "expected_route": "both"},
    ]
    rows = []
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/companies").status_code == 200
        for case in cases:
            started = time.perf_counter()
            response = client.post("/ask", json={"question": case["question"]})
            result = response.json()
            ok = response.status_code == 200 and result.get("route") == case["expected_route"]
            if ok and case["expected_route"] == "sql":
                ok = result["sql_result"]["rows"] == [[383285000000]]
            if ok and case["expected_route"] == "rag":
                ok = all(fact.casefold() in result["answer"].casefold() for fact in [
                    "Productivity and Business Processes", "Intelligent Cloud", "More Personal Computing"])
            if ok and case["expected_route"] == "both":
                ok = "sql_result" in result and bool(result["rag_result"]["citations"])
            rows.append({**case, "passed": ok, "status": response.status_code,
                         "seconds": round(time.perf_counter() - started, 2), "response": result})
            print(case["expected_route"], "PASS" if ok else "FAIL", flush=True)
    Path("reports/api_live.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    if not all(row["passed"] for row in rows):
        raise SystemExit(1)
