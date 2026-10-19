"""Recheck old artifacts, rerun browser/coding/retrieval and original tool checkpoint."""

import json, hashlib, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nexora.config import STORE
from nexora.artifacts import atomic_json
from nexora.agent_runtime import register, CodingTask, create, execute
from nexora.research import verify_checkpoint
from nexora.tool_sft import dataset, TOOLS
from nexora.model import Config, Core
from tokenizers import Tokenizer
from safetensors.torch import load_file
import torch

out = ROOT / "docs/evidence/phase9/baseline.json"
if out.exists():
    raise SystemExit("Preserve baseline evidence")
report = {"baseline_commit": "35b212b", "baseline_tests": 96, "coding": []}
for case in json.loads((ROOT / "benchmarks/coding-v1.json").read_text())["tasks"][:3]:
    for profile in ["standard", "concise"]:
        folder = STORE / "phase9" / ("baseline-" + profile + "-" + case["id"])
        folder.mkdir(parents=True, exist_ok=False)
        (folder / "solution.py").write_text(case["initial"])
        r = register(STORE, str(folder))
        task = create(
            STORE,
            CodingTask(
                repository_id=r["id"],
                path="solution.py",
                goal=case["goal"],
                acceptance=case["acceptance"],
                prompt_style=profile,
            ),
        )
        result = execute(STORE, task["id"])
        report["coding"].append(
            {
                "case": case["id"],
                "profile": profile,
                "passed": result["status"] == "awaiting_approval",
                "task": result,
            }
        )
        atomic_json(out, report)
        print(profile, case["id"], result["status"], flush=True)
folder = STORE / "tool-sft/phase8-wider-40"
result = json.loads((folder / "result.json").read_text())
model = Core(Config(**result["architecture"]))
model.load_state_dict(load_file(str(folder / "model.safetensors")))
model.eval()
torch.set_num_threads(2)
tok = Tokenizer.from_file(str(folder / "tokenizer.json"))
success = 0
schema = 0
for row in dataset()["test"]:
    ids = tok.encode(row["prompt"]).ids + [tok.token_to_id("[RESPONSE]")]
    with torch.no_grad():
        output = model.generate(torch.tensor([ids]), 48)[0].tolist()[len(ids) :]
    if tok.token_to_id("[EOS]") in output:
        output = output[: output.index(tok.token_to_id("[EOS]"))]
    try:
        p = json.loads(tok.decode(output, skip_special_tokens=False))
        valid = (
            isinstance(p, dict)
            and set(p) == {"tool", "arguments"}
            and p["tool"] in TOOLS
            and isinstance(p["arguments"], dict)
        )
        schema += valid
        success += valid and p["tool"] == row["tool"]
    except ValueError:
        pass
report["phase8_tool_reproduction"] = {"correct": success, "schema": schema, "total": 16}
cp = STORE / "runs/phase2-small-language"
verify_checkpoint(cp)
report["selected_sha256"] = hashlib.sha256(
    (cp / "checkpoints/step-0000400/model.safetensors").read_bytes()
).hexdigest()
atomic_json(out, report)
print("Core tool reproduction", success, schema, flush=True)
