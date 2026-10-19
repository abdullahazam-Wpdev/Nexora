"""Validate frozen harness and rescore stored proposals without regenerating model outputs."""

import sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nexora.config import STORE
from nexora.agent_runtime import register
from nexora.workspace_code import Task, create, execute
from nexora.artifacts import atomic_json

suite = json.loads((ROOT / "benchmarks/phase10/tasks.json").read_text())["tasks"]
tests = json.loads((ROOT / "benchmarks/phase10/acceptance.json").read_text())
report = {
    "records": [],
    "note": "Post-run harness verification; raw model evidence preserved; no new inference. Python isolated sys.path corrected; exact original benchmark hashes unchanged.",
}
final = json.loads((ROOT / "docs/evidence/phase10/coding-final.json").read_text())
byid = {r["id"]: r for r in final["records"]}
for case in suite:
    row = {"id": case["id"]}
    if case["profile"] in {"php", "fastapi", "next-component", "yaml"}:
        row.update(control_status="blocked", model_status="blocked")
    else:
        for mode in ["control", "stored"]:
            patch = tests[case["id"]]["control"]
            if mode == "stored":
                r = byid.get(case["id"], {})
                if not r.get("task_id"):
                    row["model_status"] = "blocked"
                    continue
                p = STORE / "workspace-code" / r["task_id"] / "proposal-1.json"
                if not p.exists():
                    row["model_status"] = "failed_invalid_patch"
                    continue
                patch = json.loads(p.read_text())
            repo = STORE / "phase10" / "controls" / mode / case["id"]
            repo.mkdir(parents=True, exist_ok=False)
            for name, text in case["files"].items():
                (repo / name).write_text(text)
            ident = register(STORE, str(repo))["id"]
            task = create(
                STORE,
                Task(
                    repository_id=ident,
                    files=case["scope"],
                    goal=case["request"],
                    profile=case["profile"],
                    acceptance=tests[case["id"]]["test"],
                    max_attempts=1,
                ),
            )
            r = execute(STORE, task["id"], proposer=lambda *a: patch)
            row["control_status" if mode == "control" else "model_status"] = (
                "passed" if r["status"] == "awaiting_approval" else "failed"
            )
            row[mode + "_events"] = r["events"]
            row[mode + "_error"] = r.get("error")
            row[mode + "_task_id"] = r["id"]
        if row["control_status"] != "passed":
            row["model_status"] = "blocked_harness"
    report["records"].append(row)
    atomic_json(ROOT / "docs/evidence/phase10/coding-rescore.json", report)
    print(row["id"], row.get("control_status"), row.get("model_status"), flush=True)
report["summary"] = {
    "passed": sum(r["model_status"] == "passed" for r in report["records"]),
    "failed": sum(r["model_status"].startswith("failed") for r in report["records"]),
    "blocked": sum(r["model_status"].startswith("blocked") for r in report["records"]),
    "control_passed": sum(r["control_status"] == "passed" for r in report["records"]),
}
atomic_json(ROOT / "docs/evidence/phase10/coding-rescore.json", report)
print(report["summary"])
