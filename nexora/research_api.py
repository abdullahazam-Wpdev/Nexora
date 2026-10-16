"""Functional experiment and dataset control plane. No dataset downloading over HTTP."""

import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from nexora.artifacts import identifier, atomic_json
from nexora.data_engine import build_dataset, load_dataset
from nexora.research import create_run, TrainConfig, infer_run, verify_checkpoint
from nexora import jobs


class Document(BaseModel):
    source_id: str = Field(min_length=1, max_length=160)
    text: str = Field(min_length=1, max_length=10000)


class Dataset(BaseModel):
    name: str = Field(
        min_length=1, max_length=70, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$"
    )
    documents: list[Document] = Field(min_length=3, max_length=2000)
    approved: bool = False
    license: str
    provenance: str = Field(min_length=1, max_length=2000)
    reviewer: str = Field(min_length=1, max_length=200)
    notices: dict[str, str] | None = None


class NewRun(BaseModel):
    dataset_id: str = Field(max_length=96, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
    profile: str = "tiny"
    training: dict = Field(default_factory=dict)
    start: bool = True


class Resume(BaseModel):
    steps: int = Field(default=100, ge=1, le=2000)


class Inference(BaseModel):
    prompt: str = Field(min_length=1, max_length=1024)
    max_tokens: int = Field(default=32, ge=1, le=128)


def router(store, audit):
    store = Path(store)
    r = APIRouter(prefix="/api/research", tags=["research"])

    def handle(fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except FileNotFoundError:
            raise HTTPException(404, "Artifact not found")
        except FileExistsError:
            raise HTTPException(409, "Artifact already exists")
        except (ValueError, KeyError, TypeError) as e:
            raise HTTPException(422, str(e))

    @r.get("/datasets")
    def datasets():
        return [
            json.loads(p.read_text())
            for p in (store / "datasets").glob("*/manifest.json")
        ]

    @r.post("/datasets", status_code=201)
    def ingest(body: Dataset):
        result = handle(
            build_dataset,
            body.name,
            [d.model_dump() for d in body.documents],
            approved=body.approved,
            license=body.license,
            provenance=body.provenance,
            reviewer=body.reviewer,
            notices=body.notices,
            store=store,
        )
        audit("research.dataset.approve", result["id"])
        return result

    @r.get("/datasets/{dataset_id}")
    def dataset(dataset_id: str):
        return handle(load_dataset, dataset_id, store)[0]

    @r.get("/runs")
    def runs():
        return [
            jobs.status(store, p.parent.name)
            for p in sorted((store / "runs").glob("*/result.json"), reverse=True)
        ]

    @r.get("/runs/{run_id}")
    def run(run_id: str):
        return handle(jobs.status, store, run_id)

    @r.post("/runs", status_code=202)
    def create(body: NewRun):
        if body.start and jobs.active_runs(store):
            raise HTTPException(409, "A training job is already active")
        configuration = handle(TrainConfig, **body.training)
        result = handle(
            create_run, body.dataset_id, body.profile, configuration, store=store
        )
        if body.start:
            try:
                result["job"] = jobs.launch(store, result["id"])
            except ValueError as e:
                raise HTTPException(409, str(e))
        audit("research.run.create", result["id"])
        return result

    @r.post("/runs/{run_id}/resume", status_code=202)
    def resume(run_id: str, body: Resume):
        try:
            result = jobs.launch(
                store, identifier(run_id), resume=True, steps=body.steps
            )
        except FileNotFoundError:
            raise HTTPException(404, "Run not found")
        except ValueError as e:
            raise HTTPException(409, str(e))
        audit("research.run.resume", run_id)
        return result

    @r.post("/runs/{run_id}/cancel", status_code=202)
    def cancel(run_id: str):
        try:
            result = jobs.cancel(store, identifier(run_id))
        except FileNotFoundError:
            raise HTTPException(404, "Run not found")
        except ValueError as e:
            raise HTTPException(409, str(e))
        audit("research.run.cancel", run_id)
        return result

    @r.get("/runs/{run_id}/checkpoint")
    def checkpoint(run_id: str):
        return handle(verify_checkpoint, store / "runs" / handle(identifier, run_id))[0]

    @r.post("/runs/{run_id}/generate")
    def generate(run_id: str, body: Inference):
        return handle(infer_run, run_id, body.prompt, body.max_tokens, store)

    @r.post("/runs/{run_id}/select")
    def select(run_id: str):
        handle(verify_checkpoint, store / "runs" / handle(identifier, run_id))
        atomic_json(store / "selected-model.json", {"id": run_id})
        audit("research.model.select", run_id)
        return {"id": run_id, "selected": True}

    return r
