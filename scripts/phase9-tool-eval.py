"""Schema/selection/argument probes; model proposals are not auto-executed."""

import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nexora.assistant_backend import generate
from nexora.tool_protocol import fixtures, SCHEMAS, validate_call
from nexora.artifacts import atomic_json
from nexora.generation_eval import INSTRUCTIONS

label = sys.argv[1] if len(sys.argv) > 1 else "tool-calling"
from nexora.artifacts import identifier

output = ROOT / "docs/evidence/phase9" / (identifier(label) + ".json")
if output.exists():
    raise SystemExit("Preserve existing evidence; pass a new label")
manifest = json.loads((ROOT / "tooling/reference/qwen-coder.json").read_text())
models = ["smollm2"] + (["qwen-coder"] if manifest.get("enabled") else [])
rows = []
for model in models:
    for case in fixtures():
        inference = None
        prompt = (
            "Choose one tool from "
            + ", ".join(SCHEMAS)
            + '. Return only JSON {"tool":"name","arguments":{}}.\n'
            + case["prompt"]
            + "\nSupplied parameters: "
            + json.dumps(case["expected"]["arguments"])
        )
        try:
            inference = generate(model, [{"role": "user", "content": prompt}], 96)
            text = inference["text"]
            parsed = validate_call(text)
            valid = True
            correct = parsed["tool"] == case["expected"]["tool"]
            arguments = correct and parsed["arguments"] == case["expected"]["arguments"]
            error = None
        except Exception as exc:
            valid = correct = arguments = False
            text = (inference or {}).get("text", "")
            error = str(exc)[:300]
            inference = None
        rows.append(
            {
                "model": model,
                "id": case["id"],
                "schema_valid": valid,
                "tool_correct": correct,
                "arguments_exact": arguments,
                "generated": text,
                "inference": inference,
                "error": error,
                "executed": False,
            }
        )
        atomic_json(
            output,
            {
                "protocol": "22 authored requests per provider; arguments explicitly supplied, not hidden inferred values; no model-generated shell or privileged operation is executed",
                "cases": rows,
            },
        )
    print(
        model,
        "tools",
        sum(r["tool_correct"] for r in rows if r["model"] == model),
        "/22",
        flush=True,
    )
if "qwen-coder" not in models:
    print("Qwen blocked by the resource profile; not scored")
    raise SystemExit(0)
qa = []
for case in INSTRUCTIONS:
    result = generate("qwen-coder", [{"role": "user", "content": case["prompt"]}], 32)
    qa.append(
        {
            **case,
            "generated": result["text"],
            "passed": result["text"].strip() == case["expected"],
            "inference": result,
        }
    )
atomic_json(
    ROOT / "docs/evidence/phase9/qwen-instructions.json",
    {"cases": qa, "passed": sum(r["passed"] for r in qa), "total": 4},
)
print("Qwen exact instructions", sum(r["passed"] for r in qa), "/4")
