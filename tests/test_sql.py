import pytest

from agent.sql import execute_sql, validate_sql
from eval.eval_sql import evaluate


@pytest.mark.parametrize("sql", [
    "DELETE FROM financials", "SELECT 1; DROP TABLE financials",
    "COPY financials TO 'stolen.csv'", "ATTACH 'other.duckdb' AS other",
    "SELECT * FROM read_csv('secret.csv')", "SELECT * FROM 'secret.csv'",
    "SELECT * FROM information_schema.tables", "SELECT getenv('SECRET')",
    "SELECT * FROM sqlite_scan('x','y')", "SELECT * FROM unknown_table",
    "SELECT * FROM financials CROSS JOIN financials AS b",
    "WITH RECURSIVE x AS (SELECT 1 UNION ALL SELECT 1 FROM x) SELECT * FROM x",
    "SELECT * FROM financials INTO 'x'", "PRAGMA database_list",
    "SELECT current_setting('home_directory')", "SELECT * FROM range(100000000000)",
])
def test_reject_unsafe_sql(sql):
    with pytest.raises(ValueError):
        validate_sql(sql)


def test_execution_and_missing_values(database):
    result = execute_sql("SELECT operating_income FROM financials WHERE ticker='JNJ'", database)
    assert len(result["rows"]) == 7
    assert all(row == [None] for row in result["rows"])


def test_cte_and_aggregate(database):
    result = execute_sql("WITH a AS (SELECT * FROM financials WHERE ticker='WMT') SELECT COUNT(*) FROM a", database)
    assert result["rows"] == [[8]]


def test_correlated_not_exists(database):
    result = execute_sql("""SELECT c.ticker FROM companies c WHERE NOT EXISTS (
        SELECT 1 FROM financials f WHERE f.ticker=c.ticker AND f.operating_income IS NOT NULL
        ) ORDER BY c.ticker""", database)
    assert result["rows"] == [["CVX"], ["JNJ"], ["PFE"]]


def test_all_reference_queries_match_snapshot(database):
    report = evaluate(db_path=database)
    assert report["passed"] == report["total"] == 20


def test_unknown_column_is_not_executed_as_code(database):
    import duckdb
    with pytest.raises(duckdb.Error):
        execute_sql("SELECT nonexistent FROM financials", database)
