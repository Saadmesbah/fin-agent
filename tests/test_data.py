from datetime import date

import pytest

from build_data import extract_annual, fiscal_year_for
from rag.chunk import chunk_text


@pytest.mark.parametrize("ticker,end,year", [
    ("WMT", "2026-01-31", 2026), ("NVDA", "2026-01-25", 2026),
    ("HD", "2026-02-01", 2025), ("JNJ", "2021-01-03", 2020),
    ("AAPL", "2025-09-27", 2025),
])
def test_fiscal_labels(ticker, end, year):
    assert fiscal_year_for(ticker, date.fromisoformat(end)) == year


def test_comparative_fy_is_not_period_year():
    facts = {"facts": {"us-gaap": {"Revenues": {"units": {"USD": [
        {"start": "2023-02-01", "end": "2024-01-31", "form": "10-K", "fy": 2026,
         "filed": "2026-03-01", "val": 123},
        {"start": "2023-11-01", "end": "2024-01-31", "form": "10-K", "fy": 2026,
         "filed": "2026-03-01", "val": 9},
    ]}}}}}
    assert extract_annual(facts, ["Revenues"], "WMT") == {2024: (123, "Revenues")}


def test_chunk_ids_and_empty_input():
    assert chunk_text("", "AAPL") == []
    assert chunk_text("\n  \n", "AAPL") == []
    chunks = chunk_text("\n".join(["word " * 80 for _ in range(20)]), "AAPL")
    assert len(chunks) > 1
    assert len({c["chunk_id"] for c in chunks}) == len(chunks)
    assert all(c["text"].strip() for c in chunks)
