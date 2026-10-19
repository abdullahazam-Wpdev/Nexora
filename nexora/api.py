import json
import logging
import sqlite3
from contextlib import contextmanager
import psutil
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from nexora.config import ROOT, STORE
from nexora.datasets import prepare

log = logging.getLogger("nexora")
app = FastAPI(title="NEXORA AI OS", version="0.2.0")


@contextmanager
def db():
    con = sqlite3.connect(STORE / "nexora.db")
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    try:
        yield con
        con.commit()
    finally:
        con.close()


with db() as con:
    con.executescript((ROOT / "migrations/001_initial.sql").read_text())


def audit(action, detail):
    with db() as con:
        con.execute(
            "INSERT INTO audit(actor,action,detail) VALUES(?,?,?)",
            ("local-owner", action, detail),
        )


@app.middleware("http")
async def local_write_guard(request: Request, call_next):
    # Browser mutations must originate from this local UI or direct CLI clients.
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        origin = request.headers.get("origin")
        if origin and origin not in {
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
            "http://localhost:3001",
            "http://localhost:3000",
            "http://127.0.0.1:8000",
            "http://localhost:8000",
        }:
            from fastapi.responses import JSONResponse

            return JSONResponse({"detail": "Untrusted browser origin"}, status_code=403)
    return await call_next(request)


@app.get("/api/health")
def health():
    vm = psutil.virtual_memory()
    disk = psutil.disk_usage(str(STORE))
    return {
        "status": "ok",
        "cpu_percent": psutil.cpu_percent(interval=0.05),
        "threads": psutil.cpu_count(),
        "memory_total": vm.total,
        "memory_available": vm.available,
        "disk_total": disk.total,
        "disk_free": disk.free,
        "storage_path": str(STORE),
        "device": "CPU",
        "database": "SQLite",
        "podman": "Host bridge available; run scripts/infra.py status for live container state",
    }


@app.get("/api/experiments")
def experiments():
    legacy = [json.loads(p.read_text()) for p in STORE.glob("*/result.json")]
    current = []
    for p in sorted((STORE / "runs").glob("*/result.json"), reverse=True):
        d = json.loads(p.read_text())
        if d["status"] != "completed":
            continue
        d["history"] = [
            {**row, "validation_loss": row["validation"]["loss"]}
            for row in d["history"]
            if "validation" in row
        ]
        d["config"] = {
            k: v
            for k, v in d["config"].items()
            if k in {"vocab_size", "dim", "layers", "heads", "context"}
        }
        current.append(d)
    if (STORE / "selected-model.json").exists():
        selected = json.loads((STORE / "selected-model.json").read_text())["id"]
        current.sort(key=lambda r: r["id"] != selected)
    return current + legacy


@app.get("/api/datasets")
def datasets():
    items = []
    for p in STORE.glob("*/dataset.json"):
        d = json.loads(p.read_text())
        d.pop("splits", None)
        items.append({"id": p.parent.name, **d})
    with db() as con:
        items.extend(
            {"id": r["id"], **json.loads(r["manifest"])}
            for r in con.execute("SELECT * FROM datasets")
        )
    items.extend(
        json.loads(p.read_text()) for p in (STORE / "datasets").glob("*/manifest.json")
    )
    return items


class DatasetInput(BaseModel):
    name: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")
    texts: list[str] = Field(min_length=10, max_length=1000)
    approved: bool = False
    license: str
    provenance: str = Field(max_length=2000)


@app.post("/api/datasets", status_code=201)
def ingest(body: DatasetInput):
    if sum(map(len, body.texts)) > 1_000_000:
        raise HTTPException(413, "Dataset exceeds local ingestion limit")
    try:
        manifest = prepare(
            body.texts,
            approved=body.approved,
            license=body.license,
            provenance=body.provenance,
        )
    except ValueError as e:
        raise HTTPException(422, str(e))
    try:
        with db() as con:
            con.execute(
                "INSERT INTO datasets(id,manifest) VALUES(?,?)",
                (body.name, json.dumps(manifest)),
            )
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Dataset name already exists")
    audit("dataset.ingest", body.name)
    return {"id": body.name, "documents": manifest["documents"]}


class Generation(BaseModel):
    prompt: str = Field(min_length=1, max_length=256)
    max_tokens: int = Field(default=32, ge=1, le=256)


@app.post("/api/generate")
def generate(body: Generation):
    if (
        not (STORE / "tiny-core/result.json").exists()
        and not (STORE / "selected-model.json").exists()
    ):
        raise HTTPException(409, "Train a model first")
    if (STORE / "selected-model.json").exists():
        from nexora.research import infer_run

        selected = json.loads((STORE / "selected-model.json").read_text())["id"]
        try:
            return infer_run(selected, body.prompt, body.max_tokens, STORE)
        except (ValueError, FileNotFoundError) as e:
            raise HTTPException(409, str(e))
    from nexora.train import infer

    return infer(body.prompt, body.max_tokens)


from nexora import jobs


class Training(BaseModel):
    steps: int = Field(default=160, ge=1, le=500)
    resume: bool = False
    dataset_id: str | None = Field(
        default=None, max_length=96, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$"
    )
    run_id: str | None = Field(
        default=None, max_length=96, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$"
    )
    profile: str = "tiny"


@app.get("/api/training")
def training_status():
    active = jobs.active_runs(STORE)
    return {
        "running": bool(active),
        "jobs": [{"id": r["id"], "steps": r["steps"]} for r in active],
    }


@app.post("/api/training", status_code=202)
def train(body: Training):
    from nexora.research import create_run

    if jobs.active_runs(STORE):
        raise HTTPException(409, "A training job is already running")
    try:
        if body.resume:
            run_id = body.run_id
            if not run_id and (STORE / "selected-model.json").exists():
                run_id = json.loads((STORE / "selected-model.json").read_text())["id"]
            if not run_id:
                completed = [
                    json.loads(p.read_text())
                    for p in sorted(
                        (STORE / "runs").glob("*/result.json"), reverse=True
                    )
                ]
                run_id = next(
                    (
                        r["id"]
                        for r in completed
                        if (STORE / "runs" / r["id"] / "latest.json").exists()
                    ),
                    None,
                )
            if not run_id:
                raise ValueError(
                    "No resumable research checkpoint; the original arithmetic checkpoint is preserved"
                )
            result = jobs.launch(STORE, run_id, resume=True, steps=body.steps)
        else:
            dataset_id = body.dataset_id
            if not dataset_id:
                manifests = sorted((STORE / "datasets").glob("*/manifest.json"))
                if not manifests:
                    raise ValueError("Ingest an approved research dataset first")
                dataset_id = json.loads(manifests[0].read_text())["id"]
            run = create_run(
                dataset_id, body.profile, {"steps": body.steps}, store=STORE
            )
            result = jobs.launch(STORE, run["id"])
        audit("training.start", json.dumps(body.model_dump()))
        return result
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(409, str(e))


@app.get("/api/projects")
def projects():
    with db() as con:
        return [dict(r) for r in con.execute("SELECT * FROM projects")]


class Memory(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


@app.get("/api/memory")
def memory():
    with db() as con:
        return [
            dict(r)
            for r in con.execute("SELECT * FROM memory ORDER BY id DESC LIMIT 100")
        ]


@app.post("/api/memory", status_code=201)
def add_memory(body: Memory):
    with db() as con:
        cursor = con.execute(
            "INSERT INTO memory(project_id,content) VALUES(?,?)",
            ("local", body.content),
        )
        ident = cursor.lastrowid
    audit("memory.create", str(ident))
    return {"id": ident}


@app.get("/api/audit")
def events():
    with db() as con:
        return [
            dict(r)
            for r in con.execute("SELECT * FROM audit ORDER BY id DESC LIMIT 100")
        ]


@app.get("/api/integrations")
def integrations():
    return [
        {
            "provider": "NEXORA Core",
            "purpose": "local inference",
            "status": "local",
            "cost": "free",
            "permissions": "local model artifacts",
            "authentication": "localhost only",
        },
        {
            "provider": "Ollama reference",
            "purpose": "external open-weight comparison; training disabled",
            "status": "adapter configured; check /api/reference/status for live availability",
            "cost": "local CPU and storage",
            "permissions": "fixed localhost runtime and pinned SmolLM2 model",
            "authentication": "localhost only",
        },
        {
            "provider": "External APIs",
            "status": "not configured",
            "cost": "none incurred",
            "permissions": "none granted",
            "authentication": "future environment variables",
        },
    ]


from starlette.middleware.trustedhost import TrustedHostMiddleware
from nexora.research_api import router as research_router

app.add_middleware(
    TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"]
)
app.include_router(research_router(STORE, audit))

from nexora.reference import router as reference_router

app.include_router(reference_router(audit))

from nexora.cowork import router as cowork_router

app.include_router(cowork_router(STORE, generate))

from nexora.nvidia_nim import router as nvidia_router

app.include_router(nvidia_router(audit))

from nexora.search import router as search_router

app.include_router(search_router(audit))

from nexora.browser_reader import router as browser_router

app.include_router(browser_router(audit))

from nexora.research_agent import router as research_agent_router

app.include_router(research_agent_router(audit))


@app.get("/api/cowork/providers")
def cowork_providers():
    from nexora.provider_registry import PROVIDERS

    return PROVIDERS


from nexora.agent_runtime import router as agent_router

app.include_router(agent_router(STORE))

from nexora.project_memory import router as memory_router

app.include_router(memory_router(STORE))

from nexora.openai_nim_models import router as openai_nim_router

app.include_router(openai_nim_router())

from nexora.verification import router as verification_router

app.include_router(verification_router(STORE))


@app.get("/api/agent/capabilities")
def agent_capabilities():
    from nexora.provider_registry import capabilities

    return capabilities()


from nexora.riva_speech import router as riva_router
from nexora.model_catalog import router as model_catalog_router

app.include_router(riva_router())
app.include_router(model_catalog_router())

from nexora.computer_use import router as computer_router

app.include_router(computer_router(STORE))

from nexora.document_index import router as document_router

app.include_router(document_router(STORE))


@app.get("/api/evaluations/phase8")
def phase8_evaluations():
    from nexora.config import ROOT

    folder = ROOT / "docs/evidence/phase8"
    matrix = folder / "core-matrix.json"
    if not matrix.exists():
        return {"status": "not_run", "models": []}
    import json

    data = json.loads(matrix.read_text())
    rows = [
        {
            key: row[key]
            for key in (
                "id",
                "parameters",
                "training_completion_tokens",
                "training_seconds",
                "validation",
                "test",
                "quality",
                "resources",
                "selected",
            )
        }
        for row in data["runs"]
    ]
    return {
        "status": "recorded",
        "protocol": data["protocol"],
        "models": rows,
        "warning": "Small synthetic pilot; no promoted checkpoint or professional assistant capability",
    }
