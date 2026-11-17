# Five-minute demo walkthrough

1. Start the app with `python -m uvicorn app.main:app --workers 1` from the root
   using the project venv (or `docker compose up -d`).
2. Open http://127.0.0.1:8000. Show coverage: 11 numeric companies, 3 document companies.
3. Ask “What was Apple's revenue in 2023?” Auto routing selects SQL; inspect the
   query and result 383,285,000,000 USD under Sources and SQL.
4. Ask “What are Microsoft's reportable segments?” Auto routing selects documents;
   inspect a cited passage listing all three segments.
5. Ask “What was Apple's revenue in 2023 and what outsourcing risks does Apple
   describe?” Show the combined result. Explain that the numeric year does not
   automatically date the retrieved filing or establish causality.
6. Show `reports/retrieval_*.json`, `reports/sql_live*.json` and the CI tab. Explain
   retrieval phrase hits versus exact SQL execution accuracy and provider failures.

If the model returns HTTP 429, show the committed live smoke transcript in
`reports/api_live.json` and explain the provider limit. Do not present a recorded
transcript as a fresh live request. No credentials are needed to run offline tests.
