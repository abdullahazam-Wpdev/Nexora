"""Three transparent smoke tasks: one proposal baseline vs bounded role/retry workflow."""

import json
from pathlib import Path
import resource
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nexora.agent_runtime import (
    propose,
    check_python,
    register,
    CodingTask,
    create,
    execute,
    approve,
)
from nexora.browser_reader import read_url
from nexora.cowork_sandbox import run_python
from nexora.config import STORE
from nexora.artifacts import atomic_json

out = ROOT / "docs/evidence/phase8/coding-comparison.json"
if out.exists():
    raise SystemExit(
        "Preserve existing results; choose a new evidence filename explicitly"
    )
cases = json.loads((ROOT / "benchmarks/coding-v1.json").read_text())["tasks"][:3]
report = {
    "model": "Ollama SmolLM2 135M instruct Q4, external",
    "protocol": "Three previously exposed arithmetic smoke tasks; baseline one proposal/test, roles up to two proposals with feedback and deterministic planner/tester/reviewer; shared model, sequential; not professional coding or isolated causal proof of multi-agent benefit.",
    "cases": [],
}
try:
    page = read_url("https://docs.python.org/3/library/operator.html")
    report["research"] = {
        "url": page["url"],
        "title": page["title"],
        "excerpt": page["text"][:700],
        "retrieved_at": time.time(),
    }
except Exception as exc:
    report["research"] = {"status": "unavailable", "error": str(exc)[:300]}
for case in cases:
    for mode in ["single", "roles", "control"]:
        location = STORE / "phase8" / ("coding-v2-" + mode + "-" + case["id"])
        location.mkdir(parents=True, exist_ok=True)
        source = location / "solution.py"
        if source.exists():
            raise RuntimeError("Preserve existing fixture, choose new run ID")
        source.write_text(case["initial"])
        started = time.monotonic()
        error = None
        task = None
        if mode == "single":
            try:
                code = propose("ollama", case["goal"], case["initial"])
                check_python(code)
                (location / "candidate.py").write_text(code)
                marker = "PHASE8_BASELINE_VERIFIED"
                (location / "verify.py").write_text(
                    "from pathlib import Path\nnamespace={}\nexec(compile(Path('candidate.py').read_text(),'candidate.py','exec'),namespace)\nglobals().update({k:v for k,v in namespace.items() if not k.startswith('__')})\n"
                    + case["acceptance"]
                    + "\nprint('"
                    + marker
                    + "')\n"
                )
                result = run_python(location, location / "verify.py")
                passed = result.startswith("Exit code: 0\n") and marker in result
                error = None if passed else result[-800:]
            except Exception as exc:
                passed = False
                error = str(exc)[:800]
        else:
            registered = register(STORE, str(location))
            task = create(
                STORE,
                CodingTask(
                    repository_id=registered["id"],
                    path="solution.py",
                    goal=case["goal"],
                    acceptance=case["acceptance"],
                    max_attempts=2 if mode == "roles" else 1,
                    proposed_code=case["control_patch"] if mode == "control" else None,
                ),
            )

            # The same retrieved source is included as reference, not authorization.
            def with_reference(provider, goal, original, feedback, hosted):
                return propose(
                    provider,
                    goal,
                    original,
                    report["research"].get("excerpt", "") + "\n" + feedback,
                    hosted,
                )

            task = execute(STORE, task["id"], proposer=with_reference)
            passed = task["status"] == "awaiting_approval"
            error = task.get("error")
            if passed:
                approve(STORE, task["id"], task["candidate_sha256"])
                task["final_status"] = "completed"
        row = {
            "case": case["id"],
            "mode": mode,
            "passed": passed,
            "seconds": time.monotonic() - started,
            "error": error,
            "process_lifetime_peak_rss_mb": resource.getrusage(
                resource.RUSAGE_SELF
            ).ru_maxrss
            / 1024,
        }
        if task:
            row["task"] = task
        report["cases"].append(row)
        atomic_json(out, report)
        print(mode, case["id"], passed, flush=True)
report["summary"] = {
    mode: {
        "passed": sum(r["passed"] for r in report["cases"] if r["mode"] == mode),
        "total": 3,
        "seconds": sum(r["seconds"] for r in report["cases"] if r["mode"] == mode),
    }
    for mode in ["single", "roles", "control"]
}
atomic_json(out, report)
print(json.dumps(report["summary"]))
