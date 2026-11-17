import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import duckdb
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from agent.graph import ask
from agent.llm import ROOT

# Qdrant local mode is single-process. Bound work to avoid competing model loads.
_request_lock = threading.Lock()


@asynccontextmanager
async def lifespan(app):
    yield
    from rag.index import close_client
    close_client()


app = FastAPI(title="Fin Agent", version="1.0.0", lifespan=lifespan)


class Question(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    ticker: str | None = Field(default=None, pattern=r"^[A-Za-z]{1,5}$")
    route: Literal["auto", "sql", "rag", "both"] = "auto"
    retrieval_mode: Literal["vector", "hybrid", "rerank"] = "vector"


@app.get("/health")
def health():
    return {"status": "ok", "database_ready": (ROOT / "data/processed/fin.duckdb").is_file(),
            "documents_ready": (ROOT / "data/qdrant/meta.json").is_file()}


@app.get("/companies")
def companies():
    path = ROOT / "data/processed/fin.duckdb"
    if not path.is_file():
        raise HTTPException(503, "Build the database first")
    with duckdb.connect(str(path), read_only=True) as con:
        return [{"ticker": t, "name": n, "sector": s, "documents": t in {"AAPL", "MSFT", "JNJ"}}
                for t, n, s in con.execute("SELECT ticker,name,sector FROM companies ORDER BY ticker").fetchall()]


@app.post("/ask")
def ask_question(body: Question):
    if not _request_lock.acquire(blocking=False):
        raise HTTPException(429, "Another question is running; retry shortly")
    try:
        return ask(body.question, body.ticker, body.route, body.retrieval_mode)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    except FileNotFoundError:
        raise HTTPException(503, "Required data is missing; run the data preparation commands") from None
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)) from None
    except duckdb.Error:
        raise HTTPException(422, "Generated SQL could not be executed") from None
    finally:
        _request_lock.release()


@app.get("/", include_in_schema=False)
def demo():
    return FileResponse(Path(__file__).with_name("demo.html"))
