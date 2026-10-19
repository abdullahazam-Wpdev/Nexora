"""Real documented, model-generated repair, sandbox, review and approved fixture apply."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nexora.agent_runtime import register, create, CodingTask, execute, approve
from nexora.config import STORE
from nexora.artifacts import atomic_json

repo = STORE / "phase8/verified-coding-demo"
repo.mkdir(parents=True, exist_ok=False)
case = json.loads((ROOT / "benchmarks/coding-v1.json").read_text())["tasks"][0]
(repo / "solution.py").write_text(case["initial"])
reg = register(STORE, str(repo))
task = create(
    STORE,
    CodingTask(
        repository_id=reg["id"],
        path="solution.py",
        goal=case["goal"],
        acceptance=case["acceptance"],
        prompt_style="concise",
        documentation_url="https://docs.python.org/3/library/operator.html",
    ),
)
result = execute(STORE, task["id"])
report = {
    "model": "external Ollama SmolLM2 135M, concise prompt",
    "fixture_only": True,
    "task": result,
}
if result["status"] == "awaiting_approval":
    assert (repo / "solution.py").read_text() == case["initial"]
    try:
        approve(STORE, task["id"], "0" * 64)
    except ValueError:
        report["wrong_approval_rejected"] = True
    report["approved"] = approve(STORE, task["id"], result["candidate_sha256"])
    report["final_source"] = (repo / "solution.py").read_text()
atomic_json(ROOT / "docs/evidence/phase8/coding-demo.json", report)
print(
    "Coding demo:",
    result["status"],
    "applied:",
    report.get("approved", {}).get("status"),
    "seconds:",
    result["seconds"],
)
