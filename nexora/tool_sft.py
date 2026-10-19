"""Isolated completion-only Core tool-selection pilot; never changes selected weights."""

import hashlib
import json
import math
import time
import subprocess
from dataclasses import asdict
from pathlib import Path
import torch
from torch.nn import functional as F
from tokenizers import Tokenizer, models, trainers, pre_tokenizers, decoders
from safetensors.torch import save_file, load_file
from nexora.config import STORE
from nexora.model import Core, Config
from nexora.research import Monitor, TrainConfig
from nexora.artifacts import atomic_json, sha256, identifier

TOOLS = [
    "search",
    "read_file",
    "run_tests",
    "calculator",
    "knowledge",
    "request_approval",
    "no_tool",
    "retry",
]


def dataset():
    descriptions = {
        "search": "Find fresh public documentation for topic",
        "read_file": "Read the approved project file",
        "run_tests": "Verify the staged patch using its acceptance test",
        "calculator": "Compute this arithmetic expression exactly",
        "knowledge": "Retrieve an owner-approved project note about",
        "request_approval": "Before applying a verified patch ask the owner about",
        "no_tool": "Reply politely to the greeting",
        "retry": "A temporary fetch failed; retry the same permitted source once for",
    }
    heldout = {
        "search": [
            "Find a newly published public reference.",
            "Look up recent technical documentation.",
            "Need current Python release news; consult a public source.",
            "Find authoritative evidence for a recent event online.",
        ],
        "read_file": [
            "Inspect an existing approved source file.",
            "Show the approved module contents before editing.",
            "Read the registered repository's parser source.",
            "Inspect a permitted local project file to understand its code.",
        ],
        "run_tests": [
            "Execute acceptance checks on staged code.",
            "Check the candidate with its unit suite.",
            "Validate that a staged fix satisfies deterministic assertions.",
            "Verify the patch through isolated automated tests.",
        ],
        "calculator": [
            "Evaluate seven times nineteen.",
            "Compute an exact numerical total.",
            "Calculate 17 multiplied by 23 with a computation tool.",
            "Independently evaluate the arithmetic 81 divided by 9.",
        ],
        "knowledge": [
            "Look in the saved project notes.",
            "Retrieve a previously approved preference.",
            "Recall the owner's stored Python version preference.",
            "Search approved project knowledge for an existing requirement.",
        ],
        "request_approval": [
            "Ask permission before deploying the candidate.",
            "Get owner approval before replacing live source.",
            "A tested patch is ready; request confirmation before applying it.",
            "Pause before activating a proposed skill and ask the owner.",
        ],
        "no_tool": [
            "The user greets you warmly.",
            "Answer a simple hello without fetching anything.",
            "User says good morning; answer politely without tools.",
            "Respond to a thank-you message without any external operation.",
        ],
        "retry": [
            "An approved fetch timed out; make one bounded retry.",
            "Retry one transient failure on the same permitted URL.",
            "A permitted public request returned 503; retry once within budget.",
            "Recover from a transient network error by repeating the approved fetch once.",
        ],
    }
    splits = {x: [] for x in ["train", "validation", "test"]}
    for tool in TOOLS:
        for i in range(12):
            split = "train" if i < 8 else "validation" if i < 10 else "test"
            prompt = f"Choose one tool as JSON for this task: {descriptions[tool]} sample-{i}.\nResponse:"
            if i >= 8:
                prompt = (
                    "Choose one tool as JSON for this task: "
                    + heldout[tool][i - 8]
                    + "\nResponse:"
                )
            response = json.dumps(
                {"tool": tool, "arguments": {}}, separators=(",", ":")
            )
            splits[split].append(
                {
                    "prompt": prompt,
                    "response": response,
                    "tool": tool,
                    "id": hashlib.sha256(prompt.encode()).hexdigest(),
                }
            )
    return splits


def encode_example(tokenizer, row, context):
    prefix = tokenizer.encode(row["prompt"]).ids + [tokenizer.token_to_id("[RESPONSE]")]
    completion = tokenizer.encode(row["response"]).ids + [
        tokenizer.token_to_id("[EOS]")
    ]
    sequence = prefix + completion
    if len(sequence) > context:
        raise ValueError("Example exceeds context; do not silently truncate the answer")
    x = torch.zeros(context - 1, dtype=torch.long)
    y = torch.full((context - 1,), -100, dtype=torch.long)
    x[: len(sequence) - 1] = torch.tensor(sequence[:-1])
    y[: len(sequence) - 1] = torch.tensor(sequence[1:])
    y[: len(prefix) - 1] = -100
    return x, y


from nexora.compute_budget import compute_job


@compute_job('training')
def run(
    store=STORE,
    run_id="phase7-tool-sft-paraphrase-40",
    steps=40,
    dim=64,
    layers=2,
    balanced=False,
):
    if dim not in {48, 64, 96} or layers not in {1, 2}:
        raise ValueError("Pilot architecture exceeds approved short CPU matrix")
    if not 1 <= steps <= 80:
        raise ValueError("Pilot is bounded to 80 steps")
    store = Path(store)
    folder = store / "tool-sft" / identifier(run_id)
    if folder.exists():
        raise ValueError("Run already exists; preserve it and choose a new ID")
    folder.mkdir(parents=True)
    torch.set_num_threads(2)
    torch.manual_seed(42)
    data = dataset()
    corpus = json.dumps(data, sort_keys=True)
    dataset_hash = hashlib.sha256(corpus.encode()).hexdigest()
    atomic_json(
        folder / "dataset.json",
        {
            "version": dataset_hash,
            "license": "CC0-1.0",
            "authorship": "Deterministic project-authored synthetic examples (not human-only, not proprietary assistant outputs)",
            "splits": data,
            "training_approved": True,
        },
    )
    tokenizer = Tokenizer(models.BPE(unk_token="[UNK]"))
    tokenizer.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    tokenizer.decoder = decoders.ByteLevel()
    tokenizer.train_from_iterator(
        (r["prompt"] + r["response"] for r in data["train"]),
        trainers.BpeTrainer(
            vocab_size=512,
            special_tokens=["[UNK]", "[RESPONSE]", "[EOS]"],
            initial_alphabet=pre_tokenizers.ByteLevel.alphabet(),
            show_progress=False,
        ),
    )
    tokenizer.save(str(folder / "tokenizer.json"))
    config = Config(
        vocab_size=tokenizer.get_vocab_size(),
        dim=dim,
        layers=layers,
        heads=4,
        context=128,
    )
    model = Core(config)
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.002)
    batches = {
        k: [encode_example(tokenizer, r, config.context) for r in rows]
        for k, rows in data.items()
    }
    monitor = Monitor(
        TrainConfig(
            steps=steps, max_seconds=45, max_rss_mb=650, min_available_mb=500, threads=2
        ),
        store,
    )

    def evaluate(split):
        model.eval()
        total = 0.0
        count = 0
        with torch.no_grad():
            for x, y in batches[split]:
                monitor.check()
                loss = F.cross_entropy(model(x[None]).flatten(0, 1), y, reduction="sum")
                total += loss.item()
                count += (y != -100).sum().item()
        return {
            "completion_loss": total / count,
            "completion_perplexity": math.exp(min(total / count, 80)),
            "completion_targets": count,
        }

    def quality():
        records = []
        model.eval()
        for row in data["test"]:
            monitor.check()
            ids = tokenizer.encode(row["prompt"]).ids + [
                tokenizer.token_to_id("[RESPONSE]")
            ]
            with torch.no_grad():
                out = model.generate(torch.tensor([ids]), 48)[0].tolist()[len(ids) :]
            if tokenizer.token_to_id("[EOS]") in out:
                out = out[: out.index(tokenizer.token_to_id("[EOS]"))]
            text = tokenizer.decode(out, skip_special_tokens=False)
            valid = False
            success = False
            try:
                parsed = json.loads(text)
                valid = (
                    isinstance(parsed, dict)
                    and set(parsed) == {"tool", "arguments"}
                    and parsed["tool"] in TOOLS
                    and isinstance(parsed["arguments"], dict)
                )
                success = valid and parsed["tool"] == row["tool"]
            except ValueError:
                pass
            records.append(
                {
                    "id": row["id"],
                    "response": text,
                    "schema_valid": valid,
                    "correct_tool": success,
                }
            )
        return {
            "schema_valid": sum(r["schema_valid"] for r in records),
            "tool_success": sum(r["correct_tool"] for r in records),
            "total": len(records),
            "records": records,
        }

    start = time.monotonic()
    initial = evaluate("validation")
    baseline_quality = quality()
    model.train()
    tokens = 0
    losses = []
    training_start = time.monotonic()
    cpu_start = time.process_time()
    for step in range(steps):
        monitor.check()
        indices = [(step * 4 + j) % len(batches["train"]) for j in range(4)]
        if balanced:
            indices = [
                ((step * 4 + j) % 8) * 8 + ((step * 4 + j) // 8) % 8 for j in range(4)
            ]
        x = torch.stack([batches["train"][i][0] for i in indices])
        y = torch.stack([batches["train"][i][1] for i in indices])
        optimizer.zero_grad()
        loss = F.cross_entropy(model(x).flatten(0, 1), y.flatten())
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1)
        optimizer.step()
        losses.append(loss.item())
        tokens += (y != -100).sum().item()
    training_seconds = time.monotonic() - training_start
    training_cpu_seconds = time.process_time() - cpu_start
    validation = evaluate("validation")
    test = evaluate("test")
    quality_after = quality()
    save_start = time.monotonic()
    save_file(model.state_dict(), str(folder / "model.safetensors"))
    checkpoint_seconds = time.monotonic() - save_start
    # Real roundtrip integrity/load check on the same architecture.
    restored = Core(config)
    restored.load_state_dict(load_file(str(folder / "model.safetensors")))
    assert all(
        torch.equal(v, restored.state_dict()[k]) for k, v in model.state_dict().items()
    )
    result = {
        "id": run_id,
        "format": "nexora-completion-only-pilot-v1",
        "training_code_sha256": sha256(Path(__file__)),
        "git_parent": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "code_state": "working tree; exact training script SHA recorded",
        "architecture": asdict(config),
        "parameters": sum(p.numel() for p in model.parameters()),
        "steps": steps,
        "balanced_batches": balanced,
        "training_seconds": training_seconds,
        "training_cpu_seconds": training_cpu_seconds,
        "completion_tokens_per_second": tokens / training_seconds,
        "checkpoint_seconds": checkpoint_seconds,
        "checkpoint_bytes": (folder / "model.safetensors").stat().st_size,
        "loss_masking": "Prompt and padding labels -100; only response and EOS supervised",
        "dataset_sha256": dataset_hash,
        "tokenizer_sha256": sha256(folder / "tokenizer.json"),
        "model_sha256": sha256(folder / "model.safetensors"),
        "training_completion_tokens": tokens,
        "seconds": time.monotonic() - start,
        "resources": monitor.metrics(),
        "initial_validation": initial,
        "validation": validation,
        "test": test,
        "baseline_quality": baseline_quality,
        "quality": quality_after,
        "last_train_loss": losses[-1],
        "checkpoint_roundtrip_verified": True,
        "selected": False,
        "warning": "Separate synthetic tool-selection pilot, not a capable assistant. Masked perplexity is not comparable to pretraining perplexity.",
    }
    atomic_json(folder / "result.json", result)
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="phase7-tool-sft-paraphrase-40")
    parser.add_argument("--steps", type=int, default=40)
    args = parser.parse_args()
    run(run_id=args.run_id, steps=args.steps)
