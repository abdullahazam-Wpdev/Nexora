"""Run real model proposals and isolated acceptance tests; never fabricate successes."""

import json
from pathlib import Path
import sys
import time
import argparse
import hashlib

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nexora.agent_runtime import CodingTask, register, create, execute, approve
from nexora.config import STORE

parser = argparse.ArgumentParser()
parser.add_argument("--suite", default="coding-v1")
parser.add_argument("--label")
args = parser.parse_args()
label = args.label or args.suite
suite_text = (ROOT / "benchmarks" / (args.suite + ".json")).read_text()
suite = json.loads(suite_text)
report = {
    "suite": args.suite,
    "label": label,
    "agent_code_sha256": hashlib.sha256(
        (ROOT / "nexora/agent_runtime.py").read_bytes()
    ).hexdigest(),
    "suite_sha256": hashlib.sha256(suite_text.encode()).hexdigest(),
    "disclosure": suite["provenance"],
    "provider": "Ollama external SmolLM2 135M",
    "cases": [],
    "control_cases": [],
}
root = STORE / "phase7" / label
root.mkdir(parents=True, exist_ok=True)
started = time.monotonic()
for case in suite["tasks"]:
    for mode in ["model", "control"]:
        location = root / (mode + "-" + case["id"])
        location.mkdir(exist_ok=True)
        (location / "solution.py").write_text(case["initial"])
        repository_id = register(STORE, str(location))["id"]
        task = create(
            STORE,
            CodingTask(
                repository_id=repository_id,
                path="solution.py",
                goal=case["goal"],
                acceptance=case["acceptance"],
                proposed_code=case["control_patch"] if mode == "control" else None,
                max_attempts=2 if mode == "model" else 1,
            ),
        )
        result = execute(STORE, task["id"])
        passed = result["status"] == "awaiting_approval"
        if passed:
            # This script explicitly owns only these disposable fixture repositories.
            approve(STORE, task["id"], result["candidate_sha256"])
        row = {
            k: result.get(k)
            for k in [
                "id",
                "status",
                "seconds",
                "tool_calls",
                "attempts",
                "failed_attempts",
                "unsafe_attempts",
                "error",
                "peak_rss_mb",
            ]
        }
        row.update(case=case["id"], passed=passed)
        report["cases" if mode == "model" else "control_cases"].append(row)
        (STORE / "phase7" / (label + "-results.json")).write_text(
            json.dumps(report, indent=2)
        )
        print(mode, case["id"], passed, flush=True)
report.update(
    seconds=time.monotonic() - started,
    model_passed=sum(r["passed"] for r in report["cases"]),
    model_total=len(report["cases"]),
    control_passed=sum(r["passed"] for r in report["control_cases"]),
    control_total=len(report["control_cases"]),
)
(STORE / "phase7" / (label + "-results.json")).write_text(json.dumps(report, indent=2))
print(
    json.dumps(
        {k: v for k, v in report.items() if k not in ["cases", "control_cases"]},
        indent=2,
    )
)
