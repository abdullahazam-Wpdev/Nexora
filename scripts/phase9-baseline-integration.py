"""Actual Phase 8 browser and approved-code replay without overwriting old evidence."""

import json, hashlib, time
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parent.parent
report = {}
with httpx.Client(base_url="http://127.0.0.1:8000", timeout=8) as c:
    task = c.post("/api/computer/tasks", json={"value": "Phase 9 baseline"}).json()
    ident = task["id"]
    assert (
        c.post(
            "/api/computer/tasks/" + ident + "/approve", json={"plan_sha256": "0" * 64}
        ).status_code
        == 409
    )
    c.post(
        "/api/computer/tasks/" + ident + "/approve",
        json={"plan_sha256": task["plan_sha256"]},
    ).raise_for_status()
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        task = c.get("/api/computer/tasks/" + ident).json()
        if task["status"] not in {"queued", "running"}:
            break
        time.sleep(0.2)
    assert task["status"] == "completed", task
    image = c.get("/api/computer/tasks/" + ident + "/screenshot")
    image.raise_for_status()
    expected = next(e["sha256"] for e in task["evidence"] if e["kind"] == "screenshot")
    assert hashlib.sha256(image.content).hexdigest() == expected
    (ROOT / "docs/evidence/phase9/baseline-browser.png").write_bytes(image.content)
    report["browser"] = task
    baseline = json.loads((ROOT / "docs/evidence/phase9/baseline.json").read_text())
    code = next(
        x["task"]
        for x in baseline["coding"]
        if x["case"] == "add" and x["profile"] == "concise"
    )
    current = c.get("/api/agent/tasks/" + code["id"]).json()
    if current["status"] == "awaiting_approval":
        assert (
            c.post(
                "/api/agent/tasks/" + code["id"] + "/approve",
                json={"candidate_sha256": "0" * 64},
            ).status_code
            == 409
        )
        response = c.post(
            "/api/agent/tasks/" + code["id"] + "/approve",
            json={"candidate_sha256": code["candidate_sha256"]},
        )
        response.raise_for_status()
        current = response.json()
    assert current["status"] == "completed"
    report["coding"] = current
(ROOT / "docs/evidence/phase9/baseline-integration.json").write_text(
    json.dumps(report, indent=2) + "\n"
)
print("Reproduced browser interaction/screenshot and sandboxed coding/hash approval")
source = (
    (ROOT / "scripts/phase8-quality-eval.py")
    .read_text()
    .replace(
        "docs/evidence/phase8/quality-evaluation.json",
        "docs/evidence/phase9/baseline-quality.json",
    )
)
exec(
    compile(source, "phase8-quality-eval.py", "exec"),
    {"__file__": str(ROOT / "scripts/phase8-quality-eval.py"), "__name__": "__main__"},
)
