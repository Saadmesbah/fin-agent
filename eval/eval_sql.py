"""Reference-data consistency, or live Text-to-SQL execution accuracy."""
import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import yaml

from agent.sql import DB_PATH, answer_sql, execute_sql


def equivalent(actual, expected):
    if isinstance(actual, (list, tuple)) and isinstance(expected, (list, tuple)):
        return len(actual) == len(expected) and all(equivalent(a, b) for a, b in zip(actual, expected))
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        return math.isclose(actual, expected, rel_tol=1e-6, abs_tol=1e-6)
    return actual == expected


def evaluate(live=False, db_path=DB_PATH, limit=None):
    questions = [q for q in yaml.safe_load(Path("eval/benchmark.yaml").read_text(encoding="utf-8"))
                 if q["type"] == "data"]
    rows = []
    for q in questions[:limit]:
        row = {"id": q["id"], "question": q["question"], "expected": q["expected_result"]}
        try:
            result = answer_sql(q["question"]) if live else execute_sql(q["expected_sql"], db_path)
            row.update({"actual": result["rows"], "sql": result["sql"],
                        "correct": equivalent(result["rows"], q["expected_result"])})
            if live:
                row["model"] = result["model"]
        except Exception as exc:
            row.update({"correct": False, "error": str(exc)})
        rows.append(row)
        print(q["id"], "PASS" if row["correct"] else "FAIL", flush=True)
    passed = sum(r["correct"] for r in rows)
    return {"timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "mode": "live_text_to_sql" if live else "reference_sql_consistency",
            "total": len(rows), "passed": passed, "accuracy": passed / len(rows), "questions": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output", type=Path, default=Path("reports/sql_reference.json"))
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("limit must be positive")
    report = evaluate(args.live, args.db, args.limit)
    args.output.parent.mkdir(exist_ok=True, parents=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"{report['mode']}: {report['passed']}/{report['total']}")
    if report["passed"] != report["total"]:
        raise SystemExit(1)
