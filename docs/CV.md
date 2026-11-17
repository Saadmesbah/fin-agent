# Suggested CV wording

**Finance Text-to-SQL + RAG Agent** — Python, DuckDB, Qdrant, LangGraph, FastAPI, Docker

- Built a finance assistant routing questions to validated read-only SQL and cited
  10-K retrieval across 11 companies and 882 document passages.
- Compared vector, BM25 hybrid and cross-encoder retrieval; improved phrase-based
  hit@1 from 11/13 to 13/13 on a 13-question development benchmark.
- Added API/demo, Docker and offline CI regression checks; measured 19/20 exact
  SQL results in one development run, with final rerun limited by provider quota.

Repository: https://github.com/Saadmesbah/fin-agent

Do not claim 100% answer accuracy, held-out performance, production deployment,
or completion of a final 20-question model run. The full report explains the scope.
