"""Own disposable form demonstration with real durable worker, assertions and screenshot."""

import json
from pathlib import Path
import time
import httpx

ROOT = Path(__file__).resolve().parent.parent
with httpx.Client(
    base_url="http://127.0.0.1:8000", timeout=8, trust_env=False
) as client:
    response = client.post("/api/computer/tasks", json={"value": "Phase 8 Fixture"})
    response.raise_for_status()
    task = response.json()
    ident = task["id"]
    original = client.post(
        "/api/computer/tasks/" + ident + "/approve", json={"plan_sha256": "0" * 64}
    )
    assert original.status_code == 409
    response = client.post(
        "/api/computer/tasks/" + ident + "/approve",
        json={"plan_sha256": task["plan_sha256"]},
    )
    response.raise_for_status()
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        task = client.get("/api/computer/tasks/" + ident).json()
        if task["status"] not in {"queued", "running"}:
            break
        time.sleep(0.2)
    if task["status"] != "completed":
        raise RuntimeError(task.get("error", task["status"]))
    shot = client.get("/api/computer/tasks/" + ident + "/screenshot")
    shot.raise_for_status()
    (ROOT / "docs/evidence/phase8/computer-demo.png").write_bytes(shot.content)
    (ROOT / "docs/evidence/phase8/computer-demo.json").write_text(
        json.dumps(task, indent=2) + "\n"
    )
    print(
        "Browser task completed:",
        ident,
        "seconds:",
        task["seconds"],
        "peak tree RSS MiB:",
        task.get("peak_tree_rss_mb"),
    )
