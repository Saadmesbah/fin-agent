import json
import pathlib
from datetime import date

import pandas as pd

from companies import COMPANIES

# For each metric: SEC tag names to try, in priority order.
# Companies don't agree on the name, so we list the common variants.
TAGS = {
    "revenue": [
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
    ],
    "operating_income": ["OperatingIncomeLoss"],
    "net_income": ["NetIncomeLoss"],
    "total_assets": ["Assets"],
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
}


def extract_annual(facts: dict, tags: list[str], unit: str = "USD") -> dict[int, float]:
    """Return {fiscal_year: value} for ONE metric, using annual 10-K data only."""
    us_gaap = facts["facts"].get("us-gaap", {})
    result = {}

    for tag in tags:                       # try tags in priority order
        if tag not in us_gaap:
            continue
        entries = us_gaap[tag]["units"].get(unit, [])

        # One value per period end date: keep the most recently filed one
        # (a later filing may correct an earlier number).
        best = {}
        for e in entries:
            if e.get("form") != "10-K":    # skip quarterly reports
                continue
            end = date.fromisoformat(e["end"])
            if "start" in e:               # income/cash-flow items cover a period
                days = (end - date.fromisoformat(e["start"])).days
                if not 350 <= days <= 380: # keep full years only
                    continue
            if end not in best or e["filed"] > best[end]["filed"]:
                best[end] = e

        for end, e in best.items():
            # Year-end in Jan/Feb (retailers) belongs to the previous year.
            fy = end.year - 1 if end.month <= 2 else end.year
            # setdefault: a higher-priority tag wins; later tags only fill gaps
            result.setdefault(fy, e["val"])

    return result


def build_financials(raw_dir: str = "data/raw", min_year: int = 2019):
    """Build one row per (ticker, fiscal_year). Also report gaps."""
    rows, gaps = [], []

    for ticker in COMPANIES:
        facts = json.loads((pathlib.Path(raw_dir) / f"{ticker}.json").read_text())
        per_metric = {m: extract_annual(facts, tags) for m, tags in TAGS.items()}

        years = set().union(*[set(v) for v in per_metric.values()])
        for y in sorted(y for y in years if y >= min_year):
            row = {"ticker": ticker, "fiscal_year": y}
            for m in TAGS:
                row[m] = per_metric[m].get(y)   # None if missing
            rows.append(row)

        for m, v in per_metric.items():
            n = len([y for y in v if y >= min_year])
            if n < 4:
                gaps.append((ticker, m, n))

    return pd.DataFrame(rows), gaps


if __name__ == "__main__":
    df, gaps = build_financials()
    print(df[df.ticker == "AAPL"].to_string(index=False))
    print("\nGAPS (ticker, metric, years found):")
    for g in gaps:
        print(g)