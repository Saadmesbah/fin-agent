# DuckDB schema

`companies(ticker VARCHAR, name VARCHAR, cik BIGINT, sector VARCHAR)`

`financials(ticker VARCHAR, fiscal_year BIGINT, revenue BIGINT,
operating_income DOUBLE, pretax_income DOUBLE, net_income BIGINT,
total_assets BIGINT, operating_cash_flow BIGINT)`

`ratios(ticker VARCHAR, fiscal_year BIGINT, operating_margin DOUBLE,
net_margin DOUBLE, pretax_margin DOUBLE)`

Join companies and financials USING(ticker); join ratios and financials
USING(ticker, fiscal_year). Money is in USD, not billions. Ratios are fractions.
Fiscal year labels follow each company's calendar. Revenue growth is
`(new.revenue / old.revenue - 1) * 100` for consecutive fiscal years.
NULL means missing data, never zero. Missing operating income means unavailable
under the configured SEC tags, not that the company does not disclose it anywhere.
Rows cover FY2019 onward; latest year varies. Ask SQL for available years/counts.

Tickers: AAPL Apple (Technology), MSFT Microsoft (Technology), NVDA NVIDIA
(Technology), CVX Chevron (Energy), JNJ Johnson & Johnson (Healthcare), PFE Pfizer
(Healthcare), WMT Walmart (Consumer), KO Coca-Cola (Consumer), PG Procter & Gamble
(Consumer), CAT Caterpillar (Industrials), HD Home Depot (Retail).

Margins: operating_income/revenue, net_income/revenue, pretax_income/revenue.
For percent margins multiply by 100 and round to one decimal when requested.
