"""Bounded live API/reference smoke checks; no training or model promotion."""

import hashlib
import json
import os
import subprocess
import sys
import time

import httpx

from nexora.config import ROOT, STORE

BASE = "http://127.0.0.1:8002"
OUT = STORE / "reference-verification"
OUT.mkdir(exist_ok=True)
selected = STORE / "selected-model.json"
before = hashlib.sha256(selected.read_bytes()).hexdigest()
server = None
log = (OUT / "api.log").open("a")


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
            "8002",
        ],
        cwd=ROOT,
        env={**os.environ, "NEXORA_STORAGE": str(STORE)},
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    for _ in range(50):
        if server.poll() is not None:
            raise RuntimeError("QA API exited; inspect its log")
        try:
            if httpx.get(BASE + "/api/health", timeout=2).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.1)
    raise RuntimeError("QA API did not start")


def stop():
    if server is not None and server.poll() is None:
        server.terminate()
        server.wait(timeout=10)


def request(method, path, body=None):
    response = httpx.request(method, BASE + path, json=body, timeout=70)
    response.raise_for_status()
    return response.json()


try:
    start()
    status = request("GET", "/api/reference/status")
    assert status["installed"], status
    records = []
    for prompt in [
        "Say hello in one sentence.",
        "What is 2 + 3?",
        "Return only the word blue.",
    ]:
        for provider, path in [
            ("external reference", "/api/reference/generate"),
            ("NEXORA Core", "/api/generate"),
        ]:
            started = time.monotonic()
            result = request("POST", path, {"prompt": prompt, "max_tokens": 24})
            records.append(
                {
                    "provider": provider,
                    "prompt": prompt,
                    "seconds": time.monotonic() - started,
                    "result": result,
                }
            )
            (OUT / "generation-smoke.json").write_text(
                json.dumps(records, indent=2) + "\n"
            )
    stop()
    start()
    restarted = request("GET", "/api/reference/status")
    assert restarted == status
    assert before == hashlib.sha256(selected.read_bytes()).hexdigest()
    (OUT / "verification.json").write_text(
        json.dumps(
            {
                "status": "passed",
                "api_restart_reference_persistence": True,
                "selected_checkpoint_unchanged": True,
                "selected_manifest_sha256": before,
                "reference": status,
                "generation_requests": len(records),
                "limitations": "Three smoke prompts, not a capability benchmark or matched-training comparison",
            },
            indent=2,
        )
        + "\n"
    )
    print(json.dumps({"status": "passed", "output": str(OUT)}))
finally:
    stop()
    log.close()
