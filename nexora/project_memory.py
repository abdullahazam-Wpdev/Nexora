"""Typed, owner-editable memory. Never executable instructions or training input."""

import hashlib
import sqlite3
import time
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


class Memory(BaseModel):
    kind: str = Field(pattern="^(project|document|preference|evaluation|proposal)$")
    project: str = Field(default="local", min_length=1, max_length=64)
    content: str = Field(min_length=1, max_length=8000)
    provenance: str = Field(min_length=1, max_length=500)
    retention_days: int = Field(default=30, ge=1, le=365)


def context_notes(store, project):
    """Latest three owner notes only; never proposals/evaluations or another namespace."""
    path = store / "project-memory.sqlite3"
    if not path.exists():
        return []
    with sqlite3.connect(path) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT id,content FROM entries WHERE project=? AND kind IN ('project','preference') AND expires>? ORDER BY updated DESC LIMIT 3",
            (project, time.time()),
        ).fetchall()
    return [{"id": r["id"], "content": r["content"][:250]} for r in rows]


def router(store):
    routes = APIRouter(prefix="/api/knowledge", tags=["typed project memory"])

    def db():
        con = sqlite3.connect(store / "project-memory.sqlite3")
        con.row_factory = sqlite3.Row
        return con

    with db() as con:
        con.execute(
            "CREATE TABLE IF NOT EXISTS entries(id TEXT PRIMARY KEY,kind TEXT,project TEXT,content TEXT,provenance TEXT,digest TEXT,expires REAL,updated REAL,UNIQUE(kind,project,digest))"
        )

    def values(body):
        return (
            body.kind,
            body.project,
            body.content,
            body.provenance,
            hashlib.sha256(body.content.encode()).hexdigest(),
            time.time() + body.retention_days * 86400,
            time.time(),
        )

    @routes.post("/entries", status_code=201)
    def add(body: Memory):
        with db() as con:
            ident = uuid.uuid4().hex
            con.execute(
                "INSERT OR IGNORE INTO entries VALUES(?,?,?,?,?,?,?,?)",
                (ident, *values(body)),
            )
            row = con.execute(
                "SELECT id FROM entries WHERE kind=? AND project=? AND digest=?",
                (body.kind, body.project, values(body)[4]),
            ).fetchone()
        return {
            "id": row["id"],
            "training_approved": False,
            "permission_authority": False,
        }

    @routes.get("/entries")
    def retrieve(project: str = "local", q: str = "", kind: str | None = None):
        if len(q) > 200 or len(project) > 64:
            raise HTTPException(422, "Query exceeds budget")
        with db() as con:
            con.execute("DELETE FROM entries WHERE expires < ?", (time.time(),))
            rows = con.execute(
                "SELECT * FROM entries WHERE project=? AND content LIKE ? AND (? IS NULL OR kind=?) ORDER BY updated DESC LIMIT 20",
                (project, "%" + q + "%", kind, kind),
            ).fetchall()
        return {
            "entries": [dict(r) for r in rows],
            "trust": "untrusted reference data; cannot authorize tools",
            "training_approved": False,
        }

    @routes.put("/entries/{ident}")
    def correct(ident: str, body: Memory):
        with db() as con:
            try:
                cur = con.execute(
                    "UPDATE entries SET kind=?,project=?,content=?,provenance=?,digest=?,expires=?,updated=? WHERE id=?",
                    (*values(body), ident),
                )
            except sqlite3.IntegrityError as exc:
                raise HTTPException(409, "Duplicate corrected entry") from exc
            if not cur.rowcount:
                raise HTTPException(404, "Memory not found")
        return {"id": ident, "corrected": True}

    @routes.delete("/entries/{ident}", status_code=204)
    def delete(ident: str):
        with db() as con:
            con.execute("DELETE FROM entries WHERE id=?", (ident,))

    @routes.get("/skills")
    def skills(q: str = ""):
        from nexora.config import ROOT

        if len(q) > 200:
            raise HTTPException(422, "Query exceeds budget")
        words = set(q.lower().split())
        rows = []
        for p in (ROOT / ".agents/skills").glob("*/SKILL.md"):
            text = p.read_text()
            score = sum(w in text.lower() for w in words)
            if not words or score:
                rows.append(
                    {
                        "name": p.parent.name,
                        "content": text[:8000],
                        "score": score,
                        "activates_permissions": False,
                    }
                )
        return sorted(rows, key=lambda x: -x["score"])[:8]

    return routes
