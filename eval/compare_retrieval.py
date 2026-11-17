"""Run all retrieval modes against the same benchmark and index."""
import json
from pathlib import Path

from eval.eval_retrieval import BENCHMARK_PATH, evaluate, load_questions


if __name__ == "__main__":
    Path("reports").mkdir(exist_ok=True)
    for mode in ("vector", "hybrid", "rerank"):
        print(f"\nEvaluating {mode}", flush=True)
        report = evaluate(load_questions(BENCHMARK_PATH), mode)
        Path(f"reports/retrieval_{mode}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(mode, report["scores"], flush=True)
