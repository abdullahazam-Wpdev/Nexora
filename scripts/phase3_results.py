"""Compare common immutable checkpoints; freeze selection before a single final test score."""

import json, statistics, time
import torch
from safetensors.torch import load_file
from nexora.artifacts import atomic_json, sha256
from nexora.config import STORE, ROOT
from nexora.model import Core, Config
from nexora.research import verify_checkpoint, evaluate, _mapped_tokens
from nexora.data_engine import load_dataset, canonical, shingles
from nexora.generation_eval import evaluate_generation


def main():
    torch.set_num_threads(2)
    out = ROOT / "docs/evidence/phase3"
    plan = json.loads((STORE / "phase3-plan.json").read_text())
    rows = []
    checkpoint_step = 128
    for spec in plan["runs"]:
        if spec["id"] == "phase3-base-data-s42":
            continue
        folder = STORE / "runs" / spec["id"]
        info = json.loads(
            (
                folder
                / "checkpoints"
                / f"step-{checkpoint_step:07d}"
                / "checkpoint.json"
            ).read_text()
        )
        info, cp = verify_checkpoint(folder, info)
        model = Core(Config(**info["config"]))
        model.load_state_dict(load_file(str(cp / "model.safetensors")))
        tokens = _mapped_tokens(
            folder, json.loads((folder / "tokens.json").read_text())
        )
        begin = time.monotonic()
        validation = evaluate(
            model, tokens["validation"], model.config.context, batch_size=8
        )
        current = json.loads((folder / "result.json").read_text())
        row = {
            "run_id": spec["id"],
            "seed": spec["training"]["seed"],
            "architecture": info["config"],
            "parameters": sum(p.numel() for p in model.parameters()),
            "checkpoint": info,
            "checkpoint_path": str(cp.relative_to(STORE)),
            "comparison_steps": checkpoint_step,
            "comparison_training_tokens": checkpoint_step * 1024,
            "validation": validation,
            "evaluation_seconds": time.monotonic() - begin,
            "run_status": current["status"],
            "run_last_reported_steps": current["steps"],
            "full_run_benchmark": current.get("benchmark"),
            "full_run_resources": current.get("resources"),
            "tokenizer_sha256": sha256(folder / "tokenizer.json"),
        }
        rows.append(row)
    assert len({r["tokenizer_sha256"] for r in rows}) == 1
    groups = []
    for dim in sorted({r["architecture"]["dim"] for r in rows}):
        members = [r for r in rows if r["architecture"]["dim"] == dim]
        assert len(members) == 2
        losses = [r["validation"]["loss"] for r in members]
        groups.append(
            {
                "dim": dim,
                "parameters": members[0]["parameters"],
                "seeds": [r["seed"] for r in members],
                "validation_mean": statistics.mean(losses),
                "validation_sample_std": statistics.stdev(losses),
            }
        )
    winning = min(groups, key=lambda r: r["validation_mean"])
    chosen = min(
        (r for r in rows if r["architecture"]["dim"] == winning["dim"]),
        key=lambda r: r["validation"]["loss"],
    )
    selection = {
        "run_id": chosen["run_id"],
        "checkpoint_step": checkpoint_step,
        "checkpoint": chosen["checkpoint"],
        "criterion": "Minimum validation mean across two seeds at common 131072 tokens, then minimum validation seed within winning shape. No test loss used.",
        "groups": groups,
        "token_budget": 131072,
        "planned_but_unrun": ["phase3-base-data-s42"],
        "reason": "240-second matrix limit interrupted final wider run; all six common step-128 checkpoints are available. Full-run timings cover different completion lengths and are not presented as matched-budget wall times.",
    }
    atomic_json(out / "selection-before-test.json", selection)
    folder = STORE / "runs" / chosen["run_id"]
    _, cp = verify_checkpoint(folder, chosen["checkpoint"])
    m = Core(Config(**chosen["architecture"]))
    m.load_state_dict(load_file(str(cp / "model.safetensors")))
    tokens = _mapped_tokens(folder, json.loads((folder / "tokens.json").read_text()))
    test = evaluate(m, tokens["test"], m.config.context, batch_size=8)
    manifest, docs = load_dataset(
        json.loads((folder / "result.json").read_text())["dataset_id"]
    )
    intersections = {}
    for a, b in [("train", "validation"), ("train", "test"), ("validation", "test")]:
        ag = set().union(*(shingles(d["text"]) for d in docs[a]))
        bg = set().union(*(shingles(d["text"]) for d in docs[b]))
        intersections[a + "_" + b] = {
            "exact_docs": len(
                {canonical(d["text"]) for d in docs[a]}
                & {canonical(d["text"]) for d in docs[b]}
            ),
            "source_groups": len(
                {d["source_id"] for d in docs[a]} & {d["source_id"] for d in docs[b]}
            ),
            "shared_12word_shingles": len(ag & bg),
        }
    atomic_json(
        out / "model-comparison.json",
        {
            "comparison": rows,
            "groups": groups,
            "selected": selection,
            "selected_test": test,
            "data_quality": manifest["quality"],
            "contamination": intersections,
            "limitation": "Two seeds and narrow technical source holdouts do not establish generalization to open-domain language or instruction following.",
        },
    )
    # Generate from the selected COMMON checkpoint, not its later step-256 checkpoint.
    generated = evaluate_generation(chosen["run_id"], checkpoint=chosen["checkpoint"])
    atomic_json(out / "generation-quality.json", generated)
    print(
        json.dumps(
            {
                "groups": groups,
                "chosen": chosen["run_id"],
                "checkpoint": 128,
                "test": test,
                "instruction_successes": generated["strict_instruction_successes"],
                "probes": generated["instruction_probe_count"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
