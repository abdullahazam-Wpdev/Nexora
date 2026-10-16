"""Hardware-measured, matched-token research matrix; no unbounded automatic scaling."""

import argparse
import hashlib
import os
import json
import statistics
import subprocess
import sys
import time
import torch
from nexora.artifacts import atomic_json
from nexora.config import STORE, ROOT
from nexora.model import Config, Core
from nexora.research import TrainConfig, Monitor, optimizer_for, create_run

CANDIDATES = {
    "compact": {"dim": 64, "layers": 2, "heads": 4, "context": 128},
    "baseline": {"dim": 128, "layers": 4, "heads": 4, "context": 128},
    "wider": {"dim": 192, "layers": 4, "heads": 6, "context": 128},
}


def probe(name):
    torch.set_num_threads(2)
    torch.manual_seed(42)
    c = TrainConfig(
        steps=10,
        max_seconds=30,
        max_rss_mb=800,
        min_available_mb=500,
        max_temperature=85,
        architecture=CANDIDATES[name],
    )
    monitor = Monitor(c, STORE)
    monitor.check()
    model = Core(
        Config(vocab_size=1024, **CANDIDATES[name], tie_embeddings=True, init_std=0.02)
    )
    opt = optimizer_for(model, c)
    x = torch.randint(0, 1024, (4, 128))
    y = torch.randint(0, 1024, (4, 128))
    durations = []
    for i in range(11):
        monitor.check()
        begin = time.monotonic()
        opt.zero_grad(set_to_none=True)
        for _ in range(2):
            loss = (
                torch.nn.functional.cross_entropy(model(x).flatten(0, 1), y.flatten())
                / 2
            )
            loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1, error_if_nonfinite=True)
        opt.step()
        if i >= 3:
            durations.append(time.monotonic() - begin)
    model.eval()
    ids = torch.tensor([[1, 2, 3, 4]])
    times = []
    for _ in range(3):
        monitor.check()
        start = time.monotonic()
        model.generate(ids, 32)
        times.append(time.monotonic() - start)
    seconds = statistics.median(durations)
    return {
        "candidate": name,
        "architecture": CANDIDATES[name],
        "parameters": sum(p.numel() for p in model.parameters()),
        "training_step_seconds": seconds,
        "training_tokens_per_second": 1024 / seconds,
        "seconds_per_million_training_tokens": 1e6 * seconds / 1024,
        "inference_tokens_per_second": 32 / statistics.median(times),
        "resources": monitor.metrics(),
        "warning": "Synthetic-batch computational feasibility probe; no quality score or trained checkpoint.",
    }


def plan(token_budget=262144, max_matrix_seconds=240):
    if not 1024 <= token_budget <= 262144 or token_budget % 1024:
        raise ValueError(
            "Matched token budget must be a multiple of 1024, at most 262144"
        )
    results = []
    commands = []
    evidence = ROOT / "docs/evidence/phase3"
    evidence.mkdir(parents=True, exist_ok=True)
    for name in CANDIDATES:
        cmd = [sys.executable, "-m", "nexora.scaling_experiments", "probe", name]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
        commands.append(
            {
                "command": cmd,
                "exit_code": p.returncode,
                "stdout": p.stdout,
                "stderr": p.stderr,
            }
        )
        atomic_json(evidence / "feasibility-commands.json", commands)
        if p.returncode:
            continue
        results.append(json.loads(p.stdout))
    selected = [
        r
        for r in results
        if r["resources"]["peak_rss_mb"] < 700
        and token_budget / r["training_tokens_per_second"] + 12 < 90
    ]
    if len(selected) < 2:
        raise ValueError(
            "Fewer than two configurations fit measured budgets; do not scale"
        )
    data = json.loads((STORE / "phase3-data.json").read_text())
    runs = []
    for r in selected:
        for seed in (42, 43):
            runs.append(
                {
                    "id": f"phase3-{r['candidate']}-s{seed}",
                    "dataset_id": data["expanded_dataset"],
                    "profile": "tiny",
                    "training": {
                        "steps": token_budget // 1024,
                        "schedule_steps": token_budget // 1024,
                        "warmup_steps": 16,
                        "batch_size": 4,
                        "accumulation": 2,
                        "learning_rate": 0.002,
                        "seed": seed,
                        "eval_every": 64,
                        "checkpoint_every": 64,
                        "architecture": r["architecture"],
                        "tokenizer_run": "phase2-small-language",
                        "evaluate_test": False,
                        "max_seconds": 90,
                        "max_rss_mb": 800,
                        "min_available_mb": 500,
                        "max_temperature": 85,
                    },
                }
            )
    # Dataset-size ablation keeps architecture/tokenizer/schedule/seed/budget fixed.
    if any(r["candidate"] == "baseline" for r in selected):
        matched = next(r for r in runs if r["id"] == "phase3-baseline-s42")
        runs.append(
            {
                **matched,
                "id": "phase3-base-data-s42",
                "dataset_id": data["base_dataset"],
            }
        )
    estimate = sum(
        token_budget
        / next(
            p["training_tokens_per_second"]
            for p in selected
            if p["architecture"] == r["training"]["architecture"]
        )
        + 8
        for r in runs
    )
    if estimate > max_matrix_seconds:
        raise ValueError(
            f"Estimated matrix {estimate:.1f}s exceeds aggregate budget; reduce tokens before launch"
        )
    result = {
        "token_budget": token_budget,
        "estimated_matrix_seconds": estimate,
        "max_matrix_seconds": max_matrix_seconds,
        "feasibility": results,
        "runs": runs,
        "policy": "All runs share context 128, frozen tokenizer and held-out suite. Select using validation mean across seeds; evaluate only selected winner on held-out test after selection.",
    }
    atomic_json(evidence / "scaling-plan.json", result)
    atomic_json(STORE / "phase3-plan.json", result)
    return result


def plan_fingerprint(plan):
    return hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()


def execute_plan():
    plan = json.loads((STORE / "phase3-plan.json").read_text())
    ledger_path = STORE / "phase3-execution.json"
    fingerprint = plan_fingerprint(plan)
    if ledger_path.exists():
        ledger = json.loads(ledger_path.read_text())
        if ledger["plan_sha256"] != fingerprint:
            raise ValueError(
                "Execution ledger belongs to another plan; use a separate explicitly budgeted store"
            )
    else:
        ledger = {
            "plan_sha256": fingerprint,
            "started_epoch": time.time(),
            "deadline_epoch": time.time() + plan["max_matrix_seconds"],
            "state": "running",
        }
        atomic_json(ledger_path, ledger)
    if (
        ledger.get("state") == "budget_exhausted"
        or time.time() >= ledger["deadline_epoch"]
    ):
        raise RuntimeError(
            "Persistent matrix deadline exhausted; retries cannot renew the budget"
        )
    records = []
    for spec in plan["runs"]:
        if time.time() >= ledger["deadline_epoch"]:
            raise RuntimeError(
                "Aggregate matrix wall-time budget exhausted before next run"
            )
        folder = STORE / "runs" / spec["id"]
        if folder.exists():
            from dataclasses import asdict

            existing = json.loads((folder / "result.json").read_text())
            if (
                existing["status"] != "completed"
                or existing["dataset_id"] != spec["dataset_id"]
                or existing["training"] != asdict(TrainConfig(**spec["training"]))
            ):
                raise ValueError(
                    "Existing experiment does not match a completed planned run; explicit recovery is required"
                )
            from nexora.research import verify_checkpoint

            verify_checkpoint(folder)
            records.append(
                {
                    "command": [
                        sys.executable,
                        "-m",
                        "nexora.research",
                        "train",
                        spec["id"],
                    ],
                    "exit_code": 0,
                    "reused_verified_complete": True,
                    "result": existing,
                }
            )
            atomic_json(ROOT / "docs/evidence/phase3/experiment-matrix.json", records)
            continue
        run = create_run(
            spec["dataset_id"], spec["profile"], spec["training"], spec["id"]
        )
        cmd = [sys.executable, "-m", "nexora.research", "train", run["id"]]
        with (folder / "console.log").open("w") as log:
            remaining = ledger["deadline_epoch"] - time.time()
            try:
                p = subprocess.run(
                    cmd,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    env={**os.environ, "NEXORA_STORAGE": str(STORE)},
                    cwd=ROOT,
                    timeout=min(105, max(0.1, remaining)),
                )
                exit_code = p.returncode
            except subprocess.TimeoutExpired:
                exit_code = 124
        result = json.loads((folder / "result.json").read_text())
        records.append({"command": cmd, "exit_code": exit_code, "result": result})
        atomic_json(ROOT / "docs/evidence/phase3/experiment-matrix.json", records)
        print(run["id"], result["status"], result.get("validation"), flush=True)
        if exit_code:
            print((folder / "console.log").read_text()[-1500:], flush=True)
            if exit_code == 124:
                ledger["state"] = "budget_exhausted"
                atomic_json(ledger_path, ledger)
                raise RuntimeError(
                    "Matrix time budget reached; worker interrupted and latest checkpoint retained"
                )
    ledger["state"] = "completed"
    atomic_json(ledger_path, ledger)
    return records


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("probe")
    p.add_argument("candidate", choices=CANDIDATES)
    p = sub.add_parser("plan")
    p.add_argument("--tokens", type=int, default=262144)
    p.add_argument("--max-seconds", type=int, default=240)
    sub.add_parser("run")
    args = parser.parse_args()
    if args.command == "probe":
        print(json.dumps(probe(args.candidate), indent=2))
    elif args.command == "plan":
        print(json.dumps(plan(args.tokens, args.max_seconds), indent=2))
    else:
        execute_plan()
