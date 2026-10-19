"""Measured short-prompt ablation; model proposals still face the unchanged sandbox."""

import json
from pathlib import Path
import sys
import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nexora.agent_runtime import register, create, CodingTask, execute, approve
from nexora.config import STORE
from nexora.artifacts import atomic_json

out = ROOT / "docs/evidence/phase8/short-prompt-ablation.json"
if out.exists():
    raise SystemExit("Preserve existing evidence")
rows = []
cases = json.loads((ROOT / "benchmarks/coding-v1.json").read_text())["tasks"][:3]
for case in cases:
    root = STORE / "phase8" / ("short-prompt-" + case["id"])
    root.mkdir(parents=True, exist_ok=False)
    (root / "solution.py").write_text(case["initial"])

    def short(provider, goal, original, feedback, hosted):
        with httpx.Client(timeout=20, trust_env=False) as client:
            response = client.post(
                "http://127.0.0.1:11434/api/chat",
                json={
                    "model": "smollm2:135m-instruct-q4_K_M",
                    "messages": [
                        {
                            "role": "user",
                            "content": goal
                            + "\nReturn only the complete Python function, no imports or tests.\n"
                            + original
                            + (
                                "\nPrevious error: " + feedback[-200:]
                                if feedback
                                else ""
                            ),
                        }
                    ],
                    "stream": False,
                    "keep_alive": 0,
                    "options": {
                        "num_ctx": 768,
                        "num_predict": 128,
                        "num_thread": 2,
                        "temperature": 0,
                        "seed": 42,
                    },
                },
            )
            response.raise_for_status()
            text = response.json()["message"]["content"]
        import re

        fences = re.findall(r"```(?:python)?\s*\n(.*?)```", text, re.S)
        return (fences[-1] if fences else text).strip() + "\n"

    reg = register(STORE, str(root))
    task = create(
        STORE,
        CodingTask(
            repository_id=reg["id"],
            path="solution.py",
            goal=case["goal"],
            acceptance=case["acceptance"],
        ),
    )
    result = execute(STORE, task["id"], proposer=short)
    passed = result["status"] == "awaiting_approval"
    if passed:
        approve(STORE, task["id"], result["candidate_sha256"])
    rows.append(
        {
            "case": case["id"],
            "passed": passed,
            "task": result,
            "source": "actual external SmolLM2 135M; alternate short prompt, not selected production default",
        }
    )
    atomic_json(
        out,
        {"cases": rows, "passed": sum(r["passed"] for r in rows), "total": len(rows)},
    )
    print(case["id"], passed, flush=True)
