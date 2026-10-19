"""Independent complete-token evaluation of immutable selected checkpoint."""

import sys, math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import numpy as np, torch
from safetensors.torch import load_file
from nexora.config import STORE
from nexora.model import Core, Config
from nexora.research import verify_checkpoint, evaluate
from nexora.artifacts import atomic_json
from nexora.compute_budget import admission

with admission("selected checkpoint evaluation"):
    torch.set_num_threads(2)
    folder = STORE / "runs/phase2-small-language"
    info, cp = verify_checkpoint(folder)
    model = Core(Config(**info["config"]))
    model.load_state_dict(load_file(str(cp / "model.safetensors")))
    model.eval()
    results = {
        s: evaluate(
            model,
            torch.tensor(np.load(folder / (s + ".npy")), dtype=torch.long),
            info["config"]["context"],
        )
        for s in ["validation", "test"]
    }
    for r in results.values():
        assert math.isclose(r["perplexity"], math.exp(r["loss"]), rel_tol=1e-12)
    record = {
        "parameters": sum(p.numel() for p in model.parameters()),
        "checkpoint": str(cp.relative_to(ROOT)),
        "config": info["config"],
        "evaluations": results,
        "promotion": False,
    }
    atomic_json(ROOT / "docs/evidence/phase10/selected-core.json", record)
    print(record)
