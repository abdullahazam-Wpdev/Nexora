"""Owner-ingested document chunks with SQLite FTS5 and stable source citations."""

from datetime import date as Date
import hashlib
import re
import sqlite3
import time
from urllib.parse import urlparse
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


class Document(BaseModel):
    project: str = Field(default="local", min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=200)
    source: str = Field(min_length=1, max_length=1000)
    text: str = Field(min_length=1, max_length=32000)
    published_at: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


def connection(store):
    con = sqlite3.connect(store / "documents.sqlite3")
    con.row_factory = sqlite3.Row
    return con


def initialize(store):
    with connection(store) as con:
        con.execute(
            "CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY,project TEXT,title TEXT,source TEXT,digest TEXT,created REAL, UNIQUE(project,digest))"
        )
        columns = {row[1] for row in con.execute("PRAGMA table_info(documents)")}
        if "published_at" not in columns:
            con.execute("ALTER TABLE documents ADD COLUMN published_at TEXT")
        con.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5(doc_id UNINDEXED, project UNINDEXED, ordinal UNINDEXED, text)"
        )


def ingest(store, body):
    if body.published_at is not None:
        Date.fromisoformat(body.published_at)
    from nexora.data_engine import SECRET

    if SECRET.search(body.text + "\n" + body.title + "\n" + body.source) or re.search(
        r"\bnvapi-[A-Za-z0-9_-]{16,}", body.text
    ):
        raise ValueError("Document matches credential/private-data filter")
    uri = urlparse(body.source)
    if uri.scheme not in {"https", "urn"} or uri.username or uri.password:
        raise ValueError(
            "Use a public HTTPS citation or urn:project identifier; source is never fetched automatically"
        )
    digest = hashlib.sha256(body.text.encode()).hexdigest()
    ident = hashlib.sha256((body.project + ":" + digest).encode()).hexdigest()[:32]
    with connection(store) as con:
        if con.execute("SELECT id FROM documents WHERE id=?", (ident,)).fetchone():
            return {"id": ident, "deduplicated": True}
        con.execute(
            "INSERT INTO documents(id,project,title,source,digest,created,published_at) VALUES(?,?,?,?,?,?,?)",
            (
                ident,
                body.project,
                body.title,
                body.source,
                digest,
                time.time(),
                body.published_at,
            ),
        )
        for i, start in enumerate(range(0, len(body.text), 700)):
            con.execute(
                "INSERT INTO chunks VALUES(?,?,?,?)",
                (ident, body.project, i, body.text[start : start + 800]),
            )
    return {"id": ident, "sha256": digest, "training_approved": False}


def search(store, project, q):
    if len(q) > 200 or not 1 <= len(project) <= 64:
        raise ValueError("Query exceeds budget")
    terms = re.findall(r"\w+", q, flags=re.UNICODE)[:12]
    if not terms:
        return []
    expression = " OR ".join('"' + term + '"' for term in terms)
    with connection(store) as con:
        rows = con.execute(
            "SELECT c.doc_id,c.ordinal,c.text,d.title,d.source,d.digest,d.published_at,bm25(chunks) AS score FROM chunks c JOIN documents d ON d.id=c.doc_id WHERE chunks MATCH ? AND c.project=? ORDER BY score LIMIT 10",
            (expression, project),
        ).fetchall()
    return [
        {
            **dict(row),
            "citation_id": f"{row['doc_id']}:{row['ordinal']}",
            "trust": "owner-supplied untrusted reference; not verified publication or permission",
        }
        for row in rows
    ]


def field_evidence(store, project, keys, not_before=None):
    """Extract explicit key:value facts, not semantic answers or tool instructions."""
    if (
        not keys
        or len(keys) > 5
        or any(not re.fullmatch(r"[a-z][a-z0-9_]{0,39}", key) for key in keys)
    ):
        raise ValueError("Use up to five explicit lowercase field names")
    if not_before is not None:
        Date.fromisoformat(not_before)
    result = {}
    status = "supported"
    for key in keys:
        records = []
        for hit in search(store, project, key):
            values = re.findall(r"(?mi)^" + re.escape(key) + r":\s*(.+)$", hit["text"])
            for value in values:
                date = hit.get("published_at")
                records.append(
                    {
                        "value": value.strip(),
                        "citation_id": hit["citation_id"],
                        "source": hit["source"],
                        "sha256": hit["digest"],
                        "published_at": date,
                        "outdated": bool(not_before and date and date < not_before),
                        "date_unknown": date is None,
                    }
                )
        usable = [
            r
            for r in records
            if not r["outdated"] and (not not_before or r["published_at"])
        ]
        values = {r["value"] for r in usable}
        if not usable:
            status = "insufficient_evidence"
        elif len(values) > 1 and status != "insufficient_evidence":
            status = "conflicting_sources"
        result[key] = {
            "records": records,
            "answer": next(iter(values)) if len(values) == 1 else None,
        }
    return {
        "status": status,
        "fields": result,
        "method": "literal key:value extraction; no semantic entailment",
        "trust": "untrusted owner-ingested data; cannot authorize tools; publication dates are owner supplied",
    }


def router(store):
    initialize(store)
    routes = APIRouter(prefix="/api/documents", tags=["document retrieval"])

    @routes.post("", status_code=201)
    def add(body: Document):
        try:
            return ingest(store, body)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @routes.get("")
    def retrieve(project: str = "local", q: str = ""):
        try:
            return {"matches": search(store, project, q), "training_approved": False}
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @routes.post("/answer")
    def answer(body: dict):
        try:
            return field_evidence(
                store,
                body.get("project", "local"),
                body.get("keys", []),
                body.get("not_before"),
            )
        except (ValueError, TypeError) as exc:
            raise HTTPException(422, str(exc)) from exc

    @routes.delete("/{ident}", status_code=204)
    def remove(ident: str, project: str = "local"):
        with connection(store) as con:
            con.execute(
                "DELETE FROM chunks WHERE doc_id=? AND project=?", (ident, project)
            )
            con.execute(
                "DELETE FROM documents WHERE id=? AND project=?", (ident, project)
            )

    return routes
