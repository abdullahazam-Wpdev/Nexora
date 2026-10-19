"""Owner-ingested document chunks with SQLite FTS5 and stable source citations."""

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


def connection(store):
    con = sqlite3.connect(store / "documents.sqlite3")
    con.row_factory = sqlite3.Row
    return con


def initialize(store):
    with connection(store) as con:
        con.execute(
            "CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY,project TEXT,title TEXT,source TEXT,digest TEXT,created REAL, UNIQUE(project,digest))"
        )
        con.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5(doc_id UNINDEXED, project UNINDEXED, ordinal UNINDEXED, text)"
        )


def ingest(store, body):
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
            "INSERT INTO documents VALUES(?,?,?,?,?,?)",
            (ident, body.project, body.title, body.source, digest, time.time()),
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
            "SELECT c.doc_id,c.ordinal,c.text,d.title,d.source,d.digest,bm25(chunks) AS score FROM chunks c JOIN documents d ON d.id=c.doc_id WHERE chunks MATCH ? AND c.project=? ORDER BY score LIMIT 10",
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
