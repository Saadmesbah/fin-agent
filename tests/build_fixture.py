"""Build a portable test database from the public numeric snapshot, no SEC calls."""
import argparse
from pathlib import Path

import duckdb


def build_fixture(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fixtures = Path(__file__).parent / "fixtures"
    with duckdb.connect(str(path)) as con:
        for table in ("companies", "financials"):
            con.execute(f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM read_csv_auto(?)",
                        [str(fixtures / f"{table}.csv")])
        con.execute("""CREATE OR REPLACE VIEW ratios AS SELECT ticker,fiscal_year,
            operating_income/NULLIF(revenue,0) AS operating_margin,
            net_income/NULLIF(revenue,0) AS net_margin,
            pretax_income/NULLIF(revenue,0) AS pretax_margin FROM financials""")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("data/processed/fin.duckdb"))
    build_fixture(parser.parse_args().output)
