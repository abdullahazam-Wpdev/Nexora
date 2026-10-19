"""One frozen final evaluation. Never sends acceptance or controls to the model."""

import sys, json, time, hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import psutil
from nexora.config import STORE
from nexora.artifacts import atomic_json
from nexora.agent_runtime import register
from nexora.workspace_code import Task, create, execute

out = ROOT / "docs/evidence/phase10/coding-final.json"
if out.exists():
    raise SystemExit("Final evaluation already consumed; preserve it")
base = ROOT / "benchmarks/phase10"
freeze = json.loads((base / "freeze.json").read_text())
for name, expected in freeze["files"].items():
    if hashlib.sha256((base / name).read_bytes()).hexdigest() != expected:
        raise SystemExit("Frozen fixture mismatch")
suite = json.loads((base / "tasks.json").read_text())["tasks"]
tests = json.loads((base / "acceptance.json").read_text())
report = {
    "model": "smollm2:135m-instruct-q4_K_M",
    "model_origin": "external reference, not Core",
    "prompt_version": "phase10-files-v1 (unchanged Phase9 default)",
    "freeze": freeze,
    "records": [],
    "total": len(suite),
    "budget_seconds": 180,
    "selection": "Selected for prior observed resource stability before this frozen evaluation. No post-evaluation tuning permitted.",
}
start = time.monotonic()
for case in suite:
    row = {"id": case["id"], "profile": case["profile"], "tool_call_count": 0}
    if case["profile"] in {"php", "fastapi", "next-component", "yaml"}:
        row.update(
            status="blocked",
            reason="No reviewed framework/language runtime",
            attempted=False,
        )
    elif (
        time.monotonic() - start > 180
        or psutil.virtual_memory().available < 500 * 1024**2
    ):
        row.update(
            status="blocked",
            reason="Controller runtime or available-memory budget",
            attempted=False,
        )
    else:
        repo = STORE / "phase10" / "final" / case["id"]
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
                model="smollm2",
                max_attempts=1,
            ),
        )
        before = time.monotonic()
        r = execute(STORE, task["id"])
        error = r.get("error", "")
        failure = (
            "none"
            if r["status"] == "awaiting_approval"
            else (
                "timeout"
                if "Timeout" in error or "deadline" in error
                else "invalid_patch"
                if any(
                    x in error
                    for x in [
                        "syntax",
                        "Syntax",
                        "JSON",
                        "No source",
                        "Expected",
                        "anchor",
                    ]
                )
                else "acceptance_or_generation_failure"
            )
        )
        row.update(
            status="passed" if r["status"] == "awaiting_approval" else "failed",
            failure_category=failure,
            attempted=True,
            seconds=time.monotonic() - before,
            task_id=r["id"],
            events=r["events"],
            inference=r.get("inference"),
            error=error,
            tool_call_count=sum("output" in e for e in r["events"]),
            agent_process_rss_bytes=psutil.Process().memory_info().rss,
        )
    report["records"].append(row)
    atomic_json(out, report)
    print(row["id"], row["status"], flush=True)
report["seconds"] = time.monotonic() - start
report["summary"] = {
    key: sum(r["status"] == key for r in report["records"])
    for key in ["passed", "failed", "blocked"]
}
report["attempted"] = sum(r["attempted"] for r in report["records"])
report["timeouts"] = sum(
    r.get("failure_category") == "timeout" for r in report["records"]
)
report["invalid_patches"] = sum(
    r.get("failure_category") == "invalid_patch" for r in report["records"]
)
atomic_json(out, report)
print(report["summary"])
