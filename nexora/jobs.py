"""Durable local job control shared across API restarts; no arbitrary commands."""

import json
import os
import subprocess
import sys
from pathlib import Path
import psutil
from nexora.artifacts import atomic_json, identifier, lock
from nexora.config import ROOT


def alive(pid, created):
    try:
        p = psutil.Process(pid)
        return (
            abs(p.create_time() - created) < 0.1
            and p.is_running()
            and p.status() != psutil.STATUS_ZOMBIE
        )
    except (psutil.Error, TypeError, ValueError):
        return False


def status(store, run_id):
    folder = Path(store) / "runs" / identifier(run_id)
    result = json.loads((folder / "result.json").read_text())
    launch = (
        json.loads((folder / "launch.json").read_text())
        if (folder / "launch.json").exists()
        else {}
    )
    live = alive(result.get("pid"), result.get("process_started")) or alive(
        launch.get("pid"), launch.get("process_started")
    )
    # A freshly launched resume can precede the worker's first status write.
    # Treat that interval as queued so another request cannot launch a competitor.
    if live and launch.get("process_started", 0) > result.get("started_at", 0):
        result["status"] = "queued"
    if result["status"] == "running" and not live:
        result["status"] = "interrupted"
        result["error"] = (
            "Worker exited without publishing a final status; resume from the last verified checkpoint."
        )
    if result["status"] == "queued" and launch and not live:
        result["status"] = "failed"
        result["error"] = (
            "Worker exited before acquiring the training lock. See job.log."
        )
    result["running"] = live and result["status"] in {"running", "queued"}
    result["resumable"] = (folder / "latest.json").exists()
    return result


def active_runs(store):
    result = []
    for p in (Path(store) / "runs").glob("*/result.json"):
        r = status(store, p.parent.name)
        if r["running"]:
            result.append(r)
    return result


def launch(store, run_id, *, resume=False, steps=None):
    store = Path(store)
    folder = store / "runs" / identifier(run_id)
    with lock(store / ".control.lock"):
        if active_runs(store):
            raise ValueError("A training job is already active")
        # Also coordinate with independent CLI trainers through their process-level flock.
        with lock(store / ".training.lock"):
            pass
        state = status(store, run_id)
        if resume and not state["resumable"]:
            raise ValueError("No resumable checkpoint")
        if not resume and state["status"] != "queued":
            raise ValueError(
                "Existing run cannot be overwritten; resume or create a new run"
            )
        if (folder / "cancel.request").exists():
            (folder / "cancel.request").unlink()
        args = [sys.executable, "-m", "nexora.research", "train", run_id]
        if resume:
            args.append("--resume")
        if steps is not None:
            args.extend(["--steps", str(steps)])
        with (folder / "job.log").open("a") as log:
            process = subprocess.Popen(
                args,
                cwd=ROOT,
                env={**os.environ, "NEXORA_STORAGE": str(store)},
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        atomic_json(
            folder / "launch.json",
            {
                "pid": process.pid,
                "process_started": psutil.Process(process.pid).create_time(),
                "resume": resume,
                "steps": steps,
            },
        )
        return {"id": run_id, "pid": process.pid, "status": "started"}


def cancel(store, run_id):
    state = status(store, run_id)
    if not state["running"]:
        raise ValueError("No running worker for this experiment")
    atomic_json(
        Path(store) / "runs" / identifier(run_id) / "cancel.request",
        {"requested": True, "actor": "local-owner"},
    )
    return {"id": run_id, "status": "cancellation_requested"}
