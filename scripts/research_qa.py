"""End-to-end API/worker/restart/resume/cancellation checks against isolated artifacts."""

import json, os, shutil, subprocess, sys, time
import httpx
from nexora.config import ROOT, STORE
from nexora.artifacts import atomic_json

store = STORE / "api-e2e"
store.mkdir(exist_ok=True)
source = next((STORE / "datasets").glob("python-tutorial-*/manifest.json"))
dataset = json.loads(source.read_text())["id"]
dest = store / "datasets" / dataset
if not dest.exists():
    shutil.copytree(source.parent, dest)
base = "http://127.0.0.1:8001"
log = (store / "server.log").open("a")
server = None
records = []


def start():
    global server
    server = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "nexora.api:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8001",
        ],
        cwd=ROOT,
        env={**os.environ, "NEXORA_STORAGE": str(store)},
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    for _ in range(100):
        try:
            if httpx.get(base + "/api/health").status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.1)
    raise RuntimeError("QA server did not start")


def stop():
    if server and server.poll() is None:
        server.terminate()
        server.wait(timeout=10)


def request(method, path, body=None, expected=200):
    r = httpx.request(method, base + path, json=body, timeout=30)
    records.append({"method": method, "path": path, "status": r.status_code})
    assert r.status_code == expected, r.text
    return r.json()


def wait(run_id, want):
    deadline = time.monotonic() + 100
    while time.monotonic() < deadline:
        r = request("GET", "/api/research/runs/" + run_id)
        if r["status"] in want:
            return r
        if r["status"] in {"failed", "stopped", "interrupted"}:
            raise RuntimeError(r.get("error"))
        time.sleep(0.4)
    raise RuntimeError("Worker did not reach expected status")


try:
    start()
    body = {
        "dataset_id": dataset,
        "profile": "tiny",
        "training": {
            "steps": 6,
            "checkpoint_every": 2,
            "eval_every": 2,
            "max_seconds": 90,
        },
    }
    run = request("POST", "/api/research/runs", body, 202)
    run_id = run["id"]
    request("POST", "/api/research/runs", body, 409)
    running = wait(run_id, {"running", "completed"})
    stop()
    start()
    after_restart = request("GET", "/api/research/runs/" + run_id)
    assert after_restart["status"] in {"running", "queued", "completed"}
    completed = wait(run_id, {"completed"})
    assert completed["steps"] == 6
    request("POST", "/api/research/runs/" + run_id + "/resume", {"steps": 2}, 202)
    # Wait for launch to become running before accepting the next completed state.
    deadline = time.monotonic() + 100
    while time.monotonic() < deadline:
        r = request("GET", "/api/research/runs/" + run_id)
        if r["status"] == "completed" and r["steps"] == 8:
            break
        if r["status"] in {"failed", "stopped", "interrupted"}:
            raise RuntimeError(r.get("error"))
        time.sleep(0.4)
    else:
        raise RuntimeError("Resume did not reach step 8")
    request("GET", "/api/research/runs/" + run_id + "/checkpoint")
    generation = request(
        "POST",
        "/api/research/runs/" + run_id + "/generate",
        {"prompt": "Python is", "max_tokens": 8},
    )
    request("POST", "/api/research/runs/" + run_id + "/select")
    assert (
        request("POST", "/api/generate", {"prompt": "Python is", "max_tokens": 8})[
            "model"
        ]
        == run_id
    )
    cancel_body = {**body, "training": {"steps": 2000, "max_seconds": 90}}
    cancelled = request("POST", "/api/research/runs", cancel_body, 202)["id"]
    wait(cancelled, {"running"})
    request("POST", "/api/research/runs/" + cancelled + "/cancel", expected=202)
    stopped = wait(cancelled, {"stopped"})
    assert "Cancellation requested" in stopped["error"]
    atomic_json(
        ROOT / "docs/evidence/phase2/api-e2e.json",
        {
            "checks": [
                "real worker launch",
                "duplicate-job rejection",
                "API restart with durable worker state",
                "checkpoint resume 6 to 8",
                "checkpoint verification",
                "per-run inference",
                "selected-model inference",
                "cooperative cancellation",
            ],
            "run_id": run_id,
            "after_api_restart": after_restart["status"],
            "steps_after_resume": 8,
            "generation": generation,
            "cancel_status": stopped["status"],
            "requests": records,
        },
    )
    print("API lifecycle QA passed", flush=True)
finally:
    stop()
    log.close()
