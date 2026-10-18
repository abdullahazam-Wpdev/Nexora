"""Persistent local conversations and explicit, bounded workspace actions."""

import json
import sqlite3
import threading
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from nexora import reference


class Runtime(BaseModel):
    provider: str = Field(pattern="^(ollama|localai|fcc)$")


class Turn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    provider: str = Field(default="ollama", pattern="^(ollama|core|localai|fcc)$")


def workspace_path(root: Path, name: str):
    if (
        not name
        or name.startswith("/")
        or any(p.startswith(".") for p in Path(name).parts)
    ):
        raise ValueError("Use a relative, non-hidden workspace path")
    target = (root / name).resolve()
    if not target.is_relative_to(root.resolve()) or target == root.resolve():
        raise ValueError("Path must stay inside the cowork workspace")
    return target


def command(text, root, catalog):
    """Explicit commands work independently of a model's instruction capability."""
    if text == "/help":
        return "Commands: /files, /read path, /write path followed by a newline and text, /run script.py (isolated Python), /catalog query. Files stay in the isolated cowork workspace. No host shell is exposed."
    if text == "/files":
        return (
            "\n".join(
                str(p.relative_to(root))
                for p in sorted(root.rglob("*"))
                if p.is_file()
                and not p.is_symlink()
                and not any(x.startswith(".") for x in p.relative_to(root).parts)
            )[:16000]
            or "Workspace is empty."
        )
    if text.startswith("/catalog "):
        query = text[9:].strip().lower()
        return (
            "\n".join(
                line
                for line in catalog.read_text().splitlines()
                if query in line.lower()
            )[:16000]
            or "No catalog matches. Catalog entries are references, not authenticated integrations."
        )
    if text.startswith("/run "):
        from nexora.cowork_sandbox import run_python

        return run_python(root, workspace_path(root, text[5:].strip()))
    if text.startswith("/read "):
        target = workspace_path(root, text[6:].strip())
        if not target.is_file() or target.stat().st_size > 16000:
            raise ValueError("File missing or exceeds 16 KB")
        return target.read_text()
    if text.startswith("/write "):
        name, sep, content = text[7:].partition("\n")
        if not sep:
            raise ValueError("Use /write path followed by a newline and file content")
        target = workspace_path(root, name.strip())
        if target.exists():
            raise ValueError(
                "File already exists; choose a new name to preserve your work"
            )
        if sum(1 for p in root.rglob("*") if p.is_file()) >= 100:
            raise ValueError("Workspace file budget reached (100)")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        return f"Created {name.strip()} ({len(content.encode())} bytes)."
    raise ValueError("Unknown command; use /help")


def router(store, core_generate):
    routes = APIRouter(prefix="/api/cowork", tags=["local cowork"])
    workspace = store / "coworkspace"
    workspace.mkdir(exist_ok=True)
    database = store / "cowork.sqlite3"
    catalog = Path(__file__).resolve().parent.parent / "catalogs/public-apis/README.md"
    gate = threading.Lock()

    def connect():
        con = sqlite3.connect(database, timeout=10)
        con.row_factory = sqlite3.Row
        return con

    with connect() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS threads(id TEXT PRIMARY KEY,title TEXT NOT NULL,created TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY,thread_id TEXT NOT NULL,role TEXT NOT NULL,text TEXT NOT NULL,provider TEXT NOT NULL,created TEXT DEFAULT CURRENT_TIMESTAMP);
        """)

    @routes.post("/runtime")
    def runtime(body: Runtime):
        import subprocess
        import time
        import httpx
        from nexora.config import ROOT

        if not gate.acquire(blocking=False):
            raise HTTPException(429, "A conversation turn is already running")
        acquired = reference._lock.acquire(blocking=False)
        try:
            if not acquired:
                raise HTTPException(429, "Reference inference is busy")
            from nexora import jobs

            if jobs.active_runs(store):
                raise HTTPException(
                    409, "Stop training before switching inference runtimes"
                )
            desired = "localai" if body.provider == "localai" else "ollama"
            port = 8080 if desired == "localai" else 11434

            def healthy(target):
                try:
                    with httpx.Client(trust_env=False, timeout=1) as client:
                        return client.get(target).status_code == 200
                except httpx.HTTPError:
                    return False

            def run(script, action):
                result = subprocess.run(
                    [str(ROOT / "scripts" / script), action],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                if result.returncode:
                    raise HTTPException(
                        503,
                        f"Could not {action} {script}; inspect its local service log",
                    )

            target = f"http://127.0.0.1:{port}" + (
                "/v1/models" if desired == "localai" else "/api/tags"
            )
            if not healthy(target):
                other = (
                    "http://127.0.0.1:11434/api/tags"
                    if desired == "localai"
                    else "http://127.0.0.1:8080/v1/models"
                )
                if healthy(other):
                    run("ollama.sh" if desired == "localai" else "localai.sh", "stop")
                run(desired + ".sh", "start")
                for _ in range(20):
                    if healthy(target):
                        break
                    time.sleep(0.25)
                else:
                    raise HTTPException(503, "Runtime did not become ready")
            if body.provider == "fcc" and not healthy("http://127.0.0.1:8082/health"):
                run("fcc.sh", "start")
                for _ in range(20):
                    if healthy("http://127.0.0.1:8082/health"):
                        break
                    time.sleep(0.25)
                else:
                    raise HTTPException(503, "FCC proxy did not become ready")
            return {"provider": body.provider, "ready": True, "training_enabled": False}
        except subprocess.TimeoutExpired as exc:
            raise HTTPException(
                503, "Runtime transition timed out; inspect local service status"
            ) from exc
        finally:
            if acquired:
                reference._lock.release()
            gate.release()

    @routes.get("/threads")
    def threads():
        with connect() as con:
            return [
                dict(r)
                for r in con.execute(
                    "SELECT * FROM threads ORDER BY created DESC,rowid DESC LIMIT 100"
                )
            ]

    @routes.post("/threads", status_code=201)
    def create():
        ident = uuid.uuid4().hex
        with connect() as con:
            con.execute(
                "INSERT INTO threads(id,title) VALUES(?,?)", (ident, "New conversation")
            )
        return {"id": ident}

    def exists(con, ident):
        if not con.execute("SELECT 1 FROM threads WHERE id=?", (ident,)).fetchone():
            raise HTTPException(404, "Conversation not found")

    @routes.get("/threads/{ident}")
    def messages(ident: str):
        with connect() as con:
            exists(con, ident)
            return [
                dict(r)
                for r in con.execute(
                    "SELECT * FROM messages WHERE thread_id=? ORDER BY id", (ident,)
                )
            ]

    @routes.post("/threads/{ident}/messages")
    def send(ident: str, body: Turn):
        if not gate.acquire(blocking=False):
            raise HTTPException(429, "A conversation turn is already running")
        try:
            history = messages(ident)
            if len(history) >= 200:
                raise HTTPException(409, "Conversation limit reached; start a new chat")
            with connect() as con:
                con.execute(
                    "INSERT INTO messages(thread_id,role,text,provider) VALUES(?,?,?,?)",
                    (ident, "user", body.text, body.provider),
                )
                if not history:
                    con.execute(
                        "UPDATE threads SET title=? WHERE id=?", (body.text[:60], ident)
                    )
            try:
                if body.text.startswith("/"):
                    answer = command(body.text, workspace, catalog)
                    provider = "workspace-tool"
                elif body.provider == "core":
                    from nexora.api import Generation

                    result = core_generate(
                        Generation(prompt=body.text[-256:], max_tokens=48)
                    )
                    answer = result.get(
                        "text", result.get("completion", json.dumps(result))
                    )
                    provider = "NEXORA Core • research text prediction"
                elif body.provider in {"localai", "fcc"}:
                    from nexora.local_sidecars import chat

                    context = [
                        {"role": m["role"], "content": m["text"][-500:]}
                        for m in history[-4:]
                        if m["role"] in {"user", "assistant"}
                    ]
                    answer = chat(
                        body.provider,
                        context + [{"role": "user", "content": body.text[-1000:]}],
                    )
                    provider = (
                        "LocalAI • external SmolLM2"
                        if body.provider == "localai"
                        else "FCC proxy → Ollama • external SmolLM2 (not Claude)"
                    )
                else:
                    if not reference._lock.acquire(blocking=False):
                        raise HTTPException(429, "Reference inference is busy")
                    try:
                        entries = reference.request("/api/tags").get("models", [])
                        if not any(
                            m.get("name") == reference.MODEL
                            and m.get("digest") == reference.MODEL_DIGEST
                            for m in entries
                        ):
                            raise HTTPException(
                                409, "Pinned reference model missing or changed"
                            )
                        context = [
                            {"role": m["role"], "content": m["text"][-500:]}
                            for m in history[-4:]
                            if m["role"] in {"user", "assistant"}
                        ]
                        result = reference.request(
                            "/api/chat",
                            {
                                "model": reference.MODEL,
                                "messages": context
                                + [{"role": "user", "content": body.text[-1000:]}],
                                "stream": False,
                                "keep_alive": 0,
                                "options": {
                                    "num_ctx": 512,
                                    "num_predict": 96,
                                    "num_thread": 2,
                                    "temperature": 0,
                                    "seed": 42,
                                },
                            },
                        )
                        answer = result.get("message", {}).get("content")
                        if not result.get("done") or not isinstance(answer, str):
                            raise HTTPException(503, "Incomplete model reply")
                        provider = "Ollama • external SmolLM2 135M"
                    finally:
                        reference._lock.release()
                role = "assistant"
            except (HTTPException, ValueError, OSError) as exc:
                answer = str(exc.detail) if isinstance(exc, HTTPException) else str(exc)
                provider, role = "error", "error"
            with connect() as con:
                con.execute(
                    "INSERT INTO messages(thread_id,role,text,provider) VALUES(?,?,?,?)",
                    (ident, role, answer, provider),
                )
            return {
                "role": role,
                "text": answer,
                "provider": provider,
                "training_enabled": False,
            }
        finally:
            gate.release()

    return routes
