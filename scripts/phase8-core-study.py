"""Short sequential, immutable Core experiments and selected-checkpoint verification."""

import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nexora.config import STORE
from nexora.artifacts import atomic_json

if len(sys.argv) > 1:
    from nexora.tool_sft import run

    shape = json.loads(sys.argv[1])
    with contextlib.redirect_stdout(io.StringIO()):
        result = run(
            run_id=shape["id"],
            steps=40,
            dim=shape["dim"],
            layers=shape["layers"],
            balanced=shape["balanced"],
        )
    print(json.dumps(result))
else:
    rows = []
    for name, dim, layers, balanced in [
        ("compact", 48, 1, True),
        ("baseline", 64, 2, False),
        ("balanced", 64, 2, True),
        ("wider", 96, 2, True),
    ]:
        spec = {
            "id": "phase8-" + name + "-40",
            "dim": dim,
            "layers": layers,
            "balanced": balanced,
        }
        folder = STORE / "tool-sft" / spec["id"]
        if folder.exists():
            result = json.loads((folder / "result.json").read_text())
        else:
            command = [sys.executable, __file__, json.dumps(spec)]
            p = subprocess.run(command, capture_output=True, text=True, timeout=50)
            if p.returncode:
                raise RuntimeError(p.stderr[-1500:])
            result = json.loads(p.stdout)
        rows.append(result)
        print(
            name,
            result["parameters"],
            result["quality"]["tool_success"],
            result["quality"]["schema_valid"],
            result["training_seconds"],
            flush=True,
        )
    atomic_json(
        ROOT / "docs/evidence/phase8/core-matrix.json",
        {
            "protocol": "40 steps, 4 examples per step, matched tokenizer/data/seed/context; different measured compute. Max 45s and 650MiB per run, two threads. Select by validation; test is exploratory, never promotion evidence.",
            "runs": rows,
        },
    )
    import torch
    from safetensors.torch import load_file
    from nexora.research import verify_checkpoint, evaluate, _mapped_tokens
    from nexora.model import Core, Config
    from nexora.generation_eval import evaluate_generation

    torch.set_num_threads(2)
    folder = STORE / "runs/phase2-small-language"
    info, cp = verify_checkpoint(folder)
    model = Core(Config(**info["config"]))
    model.load_state_dict(load_file(str(cp / "model.safetensors")))
    model.eval()
    arrays = _mapped_tokens(folder, json.loads((folder / "tokens.json").read_text()))
    result = {
        "parameters": sum(p.numel() for p in model.parameters()),
        "validation": evaluate(
            model, arrays["validation"], model.config.context, batch_size=8
        ),
        "test": evaluate(model, arrays["test"], model.config.context, batch_size=8),
        "generation": evaluate_generation("phase2-small-language"),
    }
    atomic_json(ROOT / "docs/evidence/phase8/selected-core.json", result)
    print("Selected Core", result["validation"], result["test"], flush=True)
