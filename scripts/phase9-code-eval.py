"""Run frozen requests with isolated held-out acceptance; preserve raw failures and controls."""

import json, sys, time, threading
from pathlib import Path
import psutil

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nexora.config import STORE
from nexora.workspace_code import Task, create, execute, approve
from nexora.agent_runtime import (
    register,
    CodingTask,
    create as old_create,
    execute as old_execute,
    approve as old_approve,
)
from nexora.artifacts import atomic_json

model = sys.argv[1] if len(sys.argv) > 1 else "qwen-coder"
label = sys.argv[2] if len(sys.argv) > 2 else model
output = ROOT / ("docs/evidence/phase9/coding-" + label + ".json")
if output.exists():
    raise SystemExit("Preserve existing evidence")
suite = json.loads((ROOT / "benchmarks/phase9-coding.json").read_text())
tests = json.loads((ROOT / "benchmarks/phase9-acceptance.json").read_text())
report = {
    "model": model,
    "origin": "external open-weight inference",
    "cases": [],
    "regression": [],
    "before_swap_bytes": psutil.swap_memory().used,
    "baseline": "Frozen 20-task suite; one proposal per final task; acceptance/control never included in prompt; blocked profiles reported separately",
}
started = time.monotonic()
stop = threading.Event()
samples = []


def monitor():
    while not stop.wait(0.1):
        rss = 0
        for p in psutil.process_iter(["name", "memory_info"]):
            try:
                if p.info["name"] and (
                    "ollama" in p.info["name"] or "runner" == p.info["name"]
                ):
                    rss += p.info["memory_info"].rss
            except psutil.Error:
                pass
        samples.append(rss)


thread = threading.Thread(target=monitor, daemon=True)
thread.start()
try:
    for case in json.loads((ROOT / "benchmarks/coding-v1.json").read_text())["tasks"][
        :3
    ]:
        folder = STORE / "phase9" / ("regression-" + label + "-" + case["id"])
        folder.mkdir(parents=True, exist_ok=False)
        (folder / "solution.py").write_text(case["initial"])
        r = register(STORE, str(folder))
        task = old_create(
            STORE,
            CodingTask(
                repository_id=r["id"],
                path="solution.py",
                goal=case["goal"],
                acceptance=case["acceptance"],
                provider="qwen-coder",
                prompt_style="concise",
            ),
        )
        task = old_execute(STORE, task["id"])
        passed = task["status"] == "awaiting_approval"
        if passed:
            old_approve(STORE, task["id"], task["candidate_sha256"])
        report["regression"].append(
            {"case": case["id"], "passed": passed, "task": task}
        )
        atomic_json(output, report)
    for case in suite["tasks"]:
        for mode in ["model", "control"]:
            if time.monotonic() - started > 180:
                report["budget_stop"] = True
                break
            root = (
                STORE / "phase9" / ("expanded-" + label + "-" + mode + "-" + case["id"])
            )
            root.mkdir(parents=True, exist_ok=False)
            for name, text in case["files"].items():
                (root / name).write_text(text)
            registered = register(STORE, str(root))
            task = create(
                STORE,
                Task(
                    repository_id=registered["id"],
                    files=list(case["files"]),
                    goal=case["request"],
                    acceptance=tests[case["id"]]["test"],
                    profile=case["profile"],
                    model=model,
                    max_attempts=1,
                ),
            )
            result = execute(
                STORE,
                task["id"],
                proposer=(lambda *args: tests[case["id"]]["patch"])
                if mode == "control"
                else None,
            )
            passed = result["status"] == "awaiting_approval"
            if passed:
                approve(STORE, result["id"], result["candidate_sha256"])
            report["cases"].append(
                {
                    "case": case["id"],
                    "profile": case["profile"],
                    "mode": mode,
                    "passed": passed,
                    "status": result["status"],
                    "seconds": result.get("seconds"),
                    "error": result.get("error"),
                    "events": result["events"],
                    "inference": result.get("inference"),
                    "task_id": result["id"],
                }
            )
            atomic_json(output, report)
            print(mode, case["id"], result["status"], flush=True)
        if report.get("budget_stop"):
            break
finally:
    stop.set()
    thread.join()
    report["seconds"] = time.monotonic() - started
    report["sampled_ollama_tree_rss_bytes"] = max(samples, default=0)
    report["after_swap_bytes"] = psutil.swap_memory().used
    report["summary"] = {
        mode: {
            "passed": sum(r["passed"] for r in report["cases"] if r["mode"] == mode),
            "executed": sum(
                r["status"] != "blocked" for r in report["cases"] if r["mode"] == mode
            ),
            "blocked": sum(
                r["status"] == "blocked" for r in report["cases"] if r["mode"] == mode
            ),
        }
        for mode in ["model", "control"]
    }
    atomic_json(output, report)
    print(json.dumps(report["summary"]))
