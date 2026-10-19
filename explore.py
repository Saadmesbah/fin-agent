import duckdb
con = duckdb.connect("data/processed/fin.duckdb")

print(con.sql("""
    SELECT ticker, fiscal_year, round(revenue/1e9, 1) AS revenue_bn
    FROM financials WHERE fiscal_year = 2023
    ORDER BY revenue DESC
""").df())

print(con.sql("""
    SELECT c.sector, round(avg(r.net_margin), 3) AS avg_net_margin
    FROM ratios r JOIN companies c USING (ticker)
    WHERE r.fiscal_year = 2023
    GROUP BY c.sector ORDER BY 2 DESC
""").df())