r"""Evaluate evidence-phrase retrieval with a supplied company filter.

Run from the project root:
    .\.venv\Scripts\python.exe -m eval.eval_retrieval
"""
from pathlib import Path
import yaml
from rag.index import search

BENCHMARK_PATH = Path("eval/benchmark.yaml")
KS = (1, 3, 5)


def load_questions(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, list):
        raise ValueError("Benchmark must contain a list of questions")
    if not all(isinstance(q, dict) for q in data):
        raise ValueError("Each benchmark entry must be a dictionary")

    questions = [q for q in data if q.get("type") == "docs"]
    if not questions:
        raise ValueError("No document questions found in benchmark")

    seen_ids = set()
    for q in questions:
        for field in ("id", "question", "company"):
            value = q.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"Question {q.get('id', '<unknown>')}: "
                    f"'{field}' must be a nonempty string"
                )

        evidence = q.get("expected_evidence")
        # Convert a single phrase into a list so both formats share one check.
        phrases = [evidence] if isinstance(evidence, str) else evidence
        if (
            not isinstance(phrases, list)
            or not phrases
            or not all(isinstance(p, str) and p.strip() for p in phrases)
        ):
            raise ValueError(
                f"{q['id']}: expected_evidence must be a nonempty string "
                "or a nonempty list of nonempty strings"
            )

        if q["id"] in seen_ids:
            raise ValueError(f"Duplicate question ID: {q['id']}")
        seen_ids.add(q["id"])
    return questions


def normalize(text: str) -> str:
    # Ignore case and repeated whitespace, but preserve punctuation and numbers.
    return " ".join(text.casefold().split())


def evidence_matches(
    text: str,
    expected_evidence: str | list[str],
) -> bool:
    phrases = (
        [expected_evidence]
        if isinstance(expected_evidence, str)
        else expected_evidence
    )

    normalized_text = normalize(text)

    return any(
        normalize(phrase) in normalized_text
        for phrase in phrases
    )


def evaluate(questions: list[dict]) -> dict:
    if not questions:
        raise ValueError("Cannot evaluate an empty question set")
    hits = {k: 0 for k in KS}
    rows = []

    for q in questions:
        results = search(q["question"], k=max(KS), ticker=q["company"])

        # A broken company filter or duplicate results invalidate the run.
        seen_chunks = set()
        for result in results:
            if result["ticker"] != q["company"]:
                raise ValueError(f"{q['id']}: search returned another company")
            key = (result["ticker"], result["chunk_id"])
            if key in seen_chunks:
                raise ValueError(f"{q['id']}: duplicate retrieved chunk {key}")
            seen_chunks.add(key)

        first_rank = None
        for rank, result in enumerate(results, start=1):
            if evidence_matches(result["text"], q["expected_evidence"]):
                first_rank = rank
                break

        for k in KS:
            if first_rank is not None and first_rank <= k:
                hits[k] += 1

        rows.append({
            "id": q["id"],
            "question": q["question"],
            "company": q["company"],
            "expected_evidence": q["expected_evidence"],
            "first_rank": first_rank,
            "retrieved_chunk_ids": [r["chunk_id"] for r in results],
        })
        print(f"{q['id']}: first matching rank = {first_rank or 'MISS'}", flush=True)

    total = len(questions)
    return {
        "total": total,
        "hits": hits,
        "scores": {k: hits[k] / total for k in KS},
        "questions": rows,
        "misses": [row for row in rows if row["first_rank"] is None],
    }


def main():
    report = evaluate(load_questions(BENCHMARK_PATH))
    print("\nVector-only retrieval with a supplied company filter")
    print("Matching: case-insensitive, whitespace-normalized substring")
    for k in KS:
        print(
            f"hit@{k}: {report['hits'][k]}/{report['total']} "
            f"({report['scores'][k]:.1%})"
        )

    scores = report["scores"]
    if not scores[1] <= scores[3] <= scores[5]:
        raise RuntimeError("Invalid scores: expected hit@1 <= hit@3 <= hit@5")

    print("\nMisses@5:")
    if not report["misses"]:
        print("None")
    for miss in report["misses"]:
        print(f"{miss['id']} ({miss['company']}): {miss['question']}")
        print(f"  Expected evidence: {miss['expected_evidence']}")
        print(f"  Retrieved chunk IDs: {miss['retrieved_chunk_ids']}")


if __name__ == "__main__":
    main()
