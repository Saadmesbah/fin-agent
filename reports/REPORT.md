# Fin Agent — implementation and evaluation report

Author: Saad Mesbah · ESI Rabat · November 17, 2026

## Objective and implementation

Build an inspectable finance assistant combining structured SEC Company Facts with
unstructured annual 10-K disclosures. The implemented system has explicit SQL,
document, and combined routes in a LangGraph state machine. FastAPI exposes the
graph through `/ask`; a small browser form displays answers, SQL and passage sources.
OpenRouter supplies the model; its key is loaded from an ignored `.env` file.

DuckDB stores companies, six financial metrics and a ratios view. The evaluated
snapshot has 11 companies and 81 company/year rows from FY2019 onward. The source
JSON hashes and compact public numeric test snapshot make local regression checks
auditable without downloading source files in CI. XOM is excluded because the
cached source identifies an incomplete holding-company entity. Operating income
is missing under configured tags for CVX, JNJ and PFE and remains NULL.

Financial-year correction: Walmart/NVIDIA January endings use the ending calendar
year; HD/JNJ early-calendar endings use the prior year. The prior global shortcut
mislabelled Walmart/NVIDIA; the first proposed replacement also lost a JNJ year.
The final regression suite covers all four. SEC `fy` is not blindly used because
comparative values can carry the fiscal year of a later filing.

## Retrieval experiment

The three extracted documents produce 882 passages: AAPL 195, JNJ 387, MSFT 300.
Whole-line chunking targets 300 words with 50-word overlap. BGE-small-en-v1.5
embeds normalized 384-dimensional vectors; query-only instruction prefix is kept.
Hybrid retrieval uses BM25 over stored passage text and reciprocal-rank fusion
`sum(1/(60+rank))`. Twenty fused candidates are rescored by
`cross-encoder/ms-marco-MiniLM-L6-v2` for the rerank mode.

All modes use the same 13 questions, corpus, and supplied company filter. A hit
means at least one passage in top-k contains any accepted evidence phrase after
case/whitespace normalization. Rankings and benchmark hash are in the JSON logs.

| Mode | Hit@1 | Hit@3 | Hit@5 |
|---|---:|---:|---:|
| Vector | 11/13, 84.6% | 13/13, 100% | 13/13, 100% |
| Hybrid | 12/13, 92.3% | 12/13, 92.3% | 13/13, 100% |
| Hybrid + reranker | 13/13, 100% | 13/13, 100% | 13/13, 100% |

Hybrid alone moves the cybersecurity phrase down to rank 4 while improving the
STELARA question. Reranking puts matching evidence first for both. This small
development set supports a measured comparison, not a claim of general superiority.
The revised AI-risk question accepts a concrete AI-model-risk sentence as an
alternative to “artificial intelligence”; its earlier phrase-only miss was a
measurement problem. Original and revised results are not directly comparable.

No generated-answer accuracy score is inferred from retrieval hits. Citations are
checked against retrieved source labels; that catches nonexistent labels but cannot
prove each claim is entailed. Two earlier manually reviewed MSFT examples and the
current three live smoke cases are examples, not a representative answer benchmark.

## SQL evaluation and failures

Twenty benchmark questions are executed against the corrected snapshot. Five
reference answers changed after fiscal-year correction: d004 MSFT; d012 CAT;
d013 adds NVDA and WMT; d014 622,174,000,000 USD; d020 eight Walmart years. d016
was clarified to ask about missing dataset values rather than company disclosure.
The pre-update and final reference logs are retained. All final reference queries
match the snapshot (20/20). This tests consistency, not model ability or independent
financial auditing of every source tag.

Live generation only sees question + schema, never reference SQL/results. Exact
result matching uses the same returned row/column shape/order and numeric tolerance
1e-6. That strict contract deliberately rejects extra company names or values.

| Run | Matches | Interpretation |
|---|---:|---|
| `sql_live_baseline.json` | 9/20 | Extra columns, one bad join, missing rounding |
| `sql_live_prompt_v2.json` | 19/20 | Output contract clarified; EXISTS over-restricted |
| `sql_live.json` | 8/20 | Final rule fix; last 12 calls returned provider HTTP 429 |

Model: `nvidia/nemotron-3.5-super-vl:free`. No failures were removed from the
denominator. EXISTS is now allowed and tested with a correlated NOT EXISTS query
against the numeric snapshot, but **a complete final-code live run is pending quota**.
Do not label 19/20 as a held-out result or claim the final code has 100% accuracy.
The prompt was revised using failures on this development set.

## Application verification

`api_live.json` records actual in-process FastAPI requests invoking LangGraph,
OpenRouter and local data. Auto SQL returned Apple's FY2023 revenue; auto RAG
listed all three MSFT segments; auto both returned SQL data and cited Apple
outsourcing evidence. All three smoke checks passed. Recorded times were 3.86,
20.85 and 20.13 seconds, respectively; they include model/network overhead and
are not a performance benchmark. Later SQL wording formatting does not change
the result rows used by these checks.

The final offline suite passed **50/50 tests on Windows** (13.56 seconds) and
**50/50 in the Linux Docker image** (8.38 seconds). The image built successfully;
its HTTP health endpoint returned 200 and Docker reported healthy. Inside that
image, the public numeric snapshot also passed all 20 reference SQL queries.
The empty image correctly reported data readiness as false until data is mounted.
See `verification.json` for the recorded checks.

The offline suite covers fiscal labels, comparative dates, NULL semantics, all
reference SQL, malicious statements/table functions, safe CTE/NOT EXISTS queries,
evidence alternatives, Qdrant reopen/filter behavior, RRF, citation validation,
graph route execution, request validation, and provider error sanitization.
CI reruns this suite without credentials or model downloads, evaluates the public
numeric snapshot, and builds/smoke-tests the Docker image. Live SQL is an optional
manually triggered workflow requiring user-provided secrets/variables.

## Deployment and limitations

Docker uses Python 3.12, CPU PyTorch, a non-root user, a host data mount and a
model-cache volume. The service binds localhost and runs one worker because
Qdrant local mode cannot be shared across application processes. Requests are
serialized with a busy response; database/index rebuilding requires stopping it.
SQL is AST-validated, uses allowed tables/functions, disables external access,
and has read-only, memory/time and result bounds. Public deployment needs additional
authentication, quotas and monitoring. Free-model availability/rate limits are
external constraints.

The numeric snapshot is derived from configured SEC tags and may include
restatements. It is not point-in-time investment data. Document vintages differ
from numerical query years; combined output does not establish causality.
Whole-line chunks sometimes exceed model token limits, which can lose evidence.
The fiscal-year policy must be rechecked for new companies/history. Broader,
held-out questions, source-page metadata, answer-level expert review, abstention
tests, and larger-scale retrieval evaluation are future extensions.

## Reproduction and evidence

Follow the root README for setup and commands. `requirements.txt` pins tested
versions; the Linux image uses CPU PyTorch of the same version. Full data and
models remain outside Git. `tests/fixtures/` contains only a small public numeric
snapshot. `reports/data_manifest.json` hashes the numeric fixtures and source JSON.
The project report and JSON logs document measured outcomes, including failures.
