"""
build_data.py -- one script that turns SEC EDGAR raw files into a clean DuckDB
database for the finance text-to-SQL + RAG project.

Run from the project root:
    python build_data.py            # downloads missing raw files, builds DB
    python build_data.py --offline  # only use data/raw/*.json already there

Output:
    data/processed/financials.csv
    data/processed/fin.duckdb   (tables: companies, financials; view: ratios)
    data/processed/data_quality.txt
"""
import argparse
import json
import pathlib
import time
from datetime import date

import pandas as pd

RAW = pathlib.Path("data/raw")
OUT = pathlib.Path("data/processed")
HEADERS = {"User-Agent": "Saad Mesbah saad.mesbah@esi.ac.ma"}  # SEC requires this

COMPANIES = {
    "AAPL": "Technology", "MSFT": "Technology", "NVDA": "Technology",
    "XOM": "Energy", "CVX": "Energy",
    "JNJ": "Healthcare", "PFE": "Healthcare",
    "WMT": "Consumer", "KO": "Consumer", "PG": "Consumer",
    "CAT": "Industrials", "HD": "Retail",
}
# A ticker is NOT a stable ID: XOM now points to a new holding company.
CIK_OVERRIDES = {"XOM": "0000034088"}

# metric -> SEC tags in priority order (first tag wins for a given year)
TAGS = {
    "revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
                "SalesRevenueNet"],
    "operating_income": ["OperatingIncomeLoss"],
    "pretax_income": [
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
    ],
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "total_assets": ["Assets"],
    "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
}
MIN_YEAR = 2019


def fetch_missing():
    import requests
    ciks = {str(v["ticker"]): str(v["cik_str"]).zfill(10) for v in requests.get(
        "https://www.sec.gov/files/company_tickers.json", headers=HEADERS).json().values()}
    RAW.mkdir(parents=True, exist_ok=True)
    for t in COMPANIES:
        p = RAW / f"{t}.json"
        if p.exists() and p.stat().st_size > 1_000_000:
            continue
        cik = CIK_OVERRIDES.get(t, ciks[t])
        r = requests.get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
                         headers=HEADERS)
        p.write_text(r.text)
        print("downloaded", t, cik, len(r.text))
        time.sleep(0.2)  # SEC limit: 10 requests/second


def extract_annual(facts, tags, unit="USD"):
    """{fiscal_year: (value, tag_used)} from annual 10-K data only."""
    gaap = facts["facts"].get("us-gaap", {})
    result = {}
    for tag in tags:
        entries = gaap.get(tag, {}).get("units", {}).get(unit, [])
        best = {}  # period end -> latest filed entry
        for e in entries:
            if e.get("form") not in ("10-K", "10-K/A"):
                continue
            end = date.fromisoformat(e["end"])
            if "start" in e:  # flow items (income, cash flow) must span ~1 year
                days = (end - date.fromisoformat(e["start"])).days
                if not 350 <= days <= 380:
                    continue
            if end not in best or e["filed"] > best[end]["filed"]:
                best[end] = e
        for end, e in best.items():
            fy = end.year - 1 if end.month <= 2 else end.year  # Jan year-ends
            result.setdefault(fy, (e["val"], tag))
    return result


def build():
    rows, companies, report = [], [], []
    for t, sector in COMPANIES.items():
        p = RAW / f"{t}.json"
        if not p.exists():
            report.append(f"SKIPPED {t}: raw file missing")
            continue
        facts = json.loads(p.read_text())
        n_assets = len(extract_annual(facts, TAGS["total_assets"]))
        if p.stat().st_size < 1_000_000 or n_assets < 4:
            report.append(f"EXCLUDED {t} ({facts.get('entityName')}): file {p.stat().st_size} bytes, "
                          f"{n_assets} annual total_assets -> wrong/incomplete SEC entity")
            continue
        per = {m: extract_annual(facts, tg) for m, tg in TAGS.items()}
        companies.append({"ticker": t, "name": facts["entityName"],
                          "cik": facts["cik"], "sector": sector})
        years = {y for v in per.values() for y in v if y >= MIN_YEAR}
        for y in sorted(years):
            row = {"ticker": t, "fiscal_year": y}
            for m in TAGS:
                row[m] = per[m][y][0] if y in per[m] else None
            rows.append(row)
        for m, v in per.items():
            n = len([y for y in v if y >= MIN_YEAR])
            tags_used = sorted({tg for y, (_, tg) in v.items() if y >= MIN_YEAR})
            if n < 4:
                report.append(f"GAP {t}.{m}: {n} years (not reported under known tags)")
            elif len(tags_used) > 1:
                report.append(f"MIXED TAGS {t}.{m}: {tags_used}")
    return pd.DataFrame(companies), pd.DataFrame(rows), report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()
    if not args.offline:
        fetch_missing()
    OUT.mkdir(parents=True, exist_ok=True)
    comp, fin, report = build()
    fin.to_csv(OUT / "financials.csv", index=False)

    import duckdb
    con = duckdb.connect(str(OUT / "fin.duckdb"))
    con.register("comp_df", comp)
    con.register("fin_df", fin)
    con.execute("CREATE OR REPLACE TABLE companies AS SELECT * FROM comp_df")
    con.execute("CREATE OR REPLACE TABLE financials AS SELECT * FROM fin_df")
    con.execute("""
        CREATE OR REPLACE VIEW ratios AS
        SELECT ticker, fiscal_year,
               operating_income / revenue AS operating_margin,
               net_income / revenue       AS net_margin,
               pretax_income / revenue    AS pretax_margin
        FROM financials""")
    (OUT / "data_quality.txt").write_text("\n".join(report))
    print(f"{len(comp)} companies, {len(fin)} rows")
    print("\n".join(report))
    print(con.sql("""SELECT ticker, min(fiscal_year) AS first, max(fiscal_year) AS last,
                     count(*) AS n FROM financials GROUP BY 1 ORDER BY 1""").df())


if __name__ == "__main__":
    main()