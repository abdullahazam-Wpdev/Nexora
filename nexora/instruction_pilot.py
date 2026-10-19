"""Original mixed instruction/argument SFT pilot; no external weights or private data."""

import hashlib, json, math, time
from pathlib import Path
from dataclasses import asdict
import torch
from torch.nn import functional as F
from tokenizers import Tokenizer, models, trainers, pre_tokenizers, decoders
from safetensors.torch import save_file, load_file
from nexora.config import STORE
from nexora.model import Core, Config
from nexora.research import Monitor, TrainConfig
from nexora.tool_sft import encode_example
from nexora.tool_protocol import fixtures, validate_call
from nexora.artifacts import atomic_json, sha256


def corpus(explicit=False):
    splits = {"train": [], "validation": [], "test": []}
    for case in fixtures():
        if explicit:
            case = {
                **case,
                "prompt": case["prompt"]
                + "\nSupplied parameters: "
                + json.dumps(case["expected"]["arguments"], sort_keys=True),
            }
        response = json.dumps(case["expected"], separators=(",", ":"))
        if case["id"].endswith("-0"):
            for i, prefix in enumerate(
                [
                    "Please: ",
                    "Task: ",
                    "Request: ",
                    "Owner asks: ",
                    "Choose an action: ",
                    "Handle this request: ",
                    "Select the appropriate operation: ",
                    "Action needed: ",
                ]
            ):
                splits["train"].append(
                    {
                        "prompt": prefix + case["prompt"],
                        "response": response,
                        "kind": "tool",
                    }
                )
            splits["validation"].append(
                {
                    "prompt": "Determine the action required: " + case["prompt"],
                    "response": response,
                    "kind": "tool",
                }
            )
        else:
            splits["test"].append(
                {"prompt": case["prompt"], "response": response, "kind": "tool"}
            )
    domains = [
        (
            "Answer the question: which day follows Monday?",
            "Tuesday",
            "Which day follows Friday?",
            "Saturday",
        ),
        (
            "Write a Python function double(x) returning x*2.",
            "def double(x):\n    return x*2",
            "Write a Python function negate(x) returning -x.",
            "def negate(x):\n    return -x",
        ),
        (
            "Return a JSON object with ready set to true.",
            '{"ready":true}',
            "Return a JSON object with active set to false.",
            '{"active":false}',
        ),
        (
            "Calculator tool returned 12. Answer with the result only.",
            "12",
            "Calculator tool returned 27. Answer with the result only.",
            "27",
        ),
        (
            "The previous answer was 8 but the verified result is 9. Give the corrected value.",
            "9",
            "The previous answer was 4 but the verified result is 6. Give the corrected value.",
            "6",
        ),
        (
            "A coding task has no repository path. Ask one clarifying question.",
            "Which repository path should I use?",
            "A file operation has no target filename. Ask one clarifying question.",
            "Which filename should I use?",
        ),
        (
            "The owner has not approved publishing. Decline that action.",
            "Publishing requires owner approval.",
            "No approval exists for a purchase. Decline that action.",
            "Purchasing requires owner approval.",
        ),
        (
            "Reply with the exact word amber.",
            "amber",
            "Reply with the exact word violet.",
            "violet",
        ),
    ]
    for i, (prompt, answer, test, expected) in enumerate(domains):
        for j, prefix in enumerate(
            [
                "",
                "Please: ",
                "Instruction: ",
                "Owner request: ",
                "Respond to: ",
                "Task: ",
                "Complete: ",
                "Answer this: ",
            ]
        ):
            splits["train"].append(
                {"prompt": prefix + prompt, "response": answer, "kind": "instruction"}
            )
        splits["validation"].append(
            {
                "prompt": "Follow this request: " + prompt,
                "response": answer,
                "kind": "instruction",
            }
        )
        splits["test"].append(
            {"prompt": test, "response": expected, "kind": "instruction"}
        )
    seen = set()
    for split, rows in splits.items():
        for row in rows:
            digest = hashlib.sha256(row["prompt"].encode()).hexdigest()
            if digest in seen:
                raise ValueError("Exact prompt contamination")
            seen.add(digest)
            row.update(
                source_id=digest,
                split=split,
                license="CC0-1.0",
                provenance="Original deterministic project-authored examples; not service outputs or private chats",
            )
    return splits


from nexora.compute_budget import compute_job


@compute_job("training")
def run(
    run_id="phase9-mixed-instruction-80",
    steps=80,
    explicit=False,
    corpus_data=None,
    evidence_phase="phase9",
):
    if evidence_phase not in {"phase9", "phase10"}:
        raise ValueError("Unknown evidence phase")
    if not 1 <= steps <= 80:
        raise ValueError("Short pilot limited to 80 steps")
    folder = STORE / "instruction-pilots" / run_id
    if folder.exists():
        raise ValueError("Preserve previous checkpoint")
    folder.mkdir(parents=True)
    data = corpus(explicit) if corpus_data is None else corpus_data
    atomic_json(
        folder / "dataset.json",
        {
            "splits": data,
            "training_approved": True,
            "license": "CC0-1.0",
            "revision": (
                "phase10-disjoint-values-v1"
                if corpus_data is not None
                else ("phase9-explicit-v2" if explicit else "phase9-original-v1")
            ),
            "warning": "Small synthetic pilot; see split/source records for overlap and generalization limits.",
        },
    )
    torch.set_num_threads(2)
    torch.manual_seed(42)
    tok = Tokenizer(models.BPE(unk_token="[UNK]"))
    tok.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    tok.decoder = decoders.ByteLevel()
    tok.train_from_iterator(
        (r["prompt"] + r["response"] for r in data["train"]),
        trainers.BpeTrainer(
            vocab_size=768,
            special_tokens=["[UNK]", "[RESPONSE]", "[EOS]"],
            initial_alphabet=pre_tokenizers.ByteLevel.alphabet(),
            show_progress=False,
        ),
    )
    tok.save(str(folder / "tokenizer.json"))
    config = Config(
        vocab_size=tok.get_vocab_size(), dim=96, layers=2, heads=4, context=192
    )
    model = Core(config)
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.002)
    batches = {
        s: [encode_example(tok, r, config.context) for r in rows]
        for s, rows in data.items()
    }
    monitor = Monitor(
        TrainConfig(
            steps=steps, max_seconds=45, max_rss_mb=650, min_available_mb=500, threads=2
        ),
        STORE,
    )

    def evaluate(split):
        model.eval()
        loss = 0
        count = 0
        with torch.no_grad():
            for x, y in batches[split]:
                monitor.check()
                loss += F.cross_entropy(
                    model(x[None]).flatten(0, 1), y, reduction="sum"
                ).item()
                count += (y != -100).sum().item()
        return {"loss": loss / count, "perplexity": math.exp(min(loss / count, 80))}

    initial = evaluate("validation")
    start = time.monotonic()
    cpu = time.process_time()
    tokens = 0
    order = torch.randperm(
        len(batches["train"]), generator=torch.Generator().manual_seed(43)
    ).tolist()
    model.train()
    for step in range(steps):
        monitor.check()
        selected = [
            batches["train"][order[(step * 4 + j) % len(order)]] for j in range(4)
        ]
        x = torch.stack([r[0] for r in selected])
        y = torch.stack([r[1] for r in selected])
        optimizer.zero_grad()
        loss = F.cross_entropy(model(x).flatten(0, 1), y.flatten())
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1)
        optimizer.step()
        tokens += (y != -100).sum().item()
    train_seconds = time.monotonic() - start
    cpu_seconds = time.process_time() - cpu
    validation = evaluate("validation")
    test = evaluate("test")
    records = []
    model.eval()
    for row in data["test"]:
        monitor.check()
        ids = tok.encode(row["prompt"]).ids + [tok.token_to_id("[RESPONSE]")]
        with torch.no_grad():
            out = model.generate(torch.tensor([ids]), 64)[0].tolist()[len(ids) :]
        if tok.token_to_id("[EOS]") in out:
            out = out[: out.index(tok.token_to_id("[EOS]"))]
        text = tok.decode(out, skip_special_tokens=False)
        valid = False
        correct = False
        if row["kind"] == "tool":
            try:
                parsed = validate_call(text)
                valid = True
                correct = parsed["tool"] == json.loads(row["response"])["tool"]
            except (ValueError, TypeError):
                pass
        records.append(
            {
                "kind": row["kind"],
                "prompt": row["prompt"],
                "expected": row["response"],
                "generated": text,
                "exact": text.strip() == row["response"].strip(),
                "schema_valid": valid,
                "tool_correct": correct,
            }
        )
    save_file(model.state_dict(), str(folder / "model.safetensors"))
    restored = Core(config)
    restored.load_state_dict(load_file(str(folder / "model.safetensors")))
    assert all(
        torch.equal(v, restored.state_dict()[k]) for k, v in model.state_dict().items()
    )
    result = {
        "id": run_id,
        "architecture": asdict(config),
        "parameters": sum(p.numel() for p in model.parameters()),
        "steps": steps,
        "initial_validation": initial,
        "validation": validation,
        "test": test,
        "completion_tokens": tokens,
        "train_seconds": train_seconds,
        "cpu_seconds": cpu_seconds,
        "completion_tokens_per_second": tokens / train_seconds,
        "resources": monitor.metrics(),
        "records": records,
        "tool_schema_valid": sum(r["schema_valid"] for r in records),
        "tool_correct": sum(r["tool_correct"] for r in records),
        "tool_total": sum(r["kind"] == "tool" for r in records),
        "explicit_parameters": explicit,
        "instruction_exact": sum(
            r["exact"] for r in records if r["kind"] == "instruction"
        ),
        "instruction_total": sum(r["kind"] == "instruction" for r in records),
        "checkpoint_sha256": sha256(folder / "model.safetensors"),
        "dataset_sha256": sha256(folder / "dataset.json"),
        "code_sha256": sha256(Path(__file__)),
        "selected": False,
        "warning": "Separate random-init Core research, not external fine-tuning or a promoted Core 2.0 model",
    }
    atomic_json(folder / "result.json", result)
    atomic_json(
        Path(__file__).resolve().parent.parent
        / (
            ("docs/evidence/phase10/" + run_id + ".json")
            if evidence_phase == "phase10"
            else (
                "docs/evidence/phase9/instruction-pilot-explicit.json"
                if explicit
                else "docs/evidence/phase9/instruction-pilot.json"
            )
        ),
        result,
    )
    print(
        "Mixed pilot",
        result["tool_correct"],
        "/" + str(result["tool_total"]) + " tools;",
        result["instruction_exact"],
        "/" + str(result["instruction_total"]) + " instructions",
    )
    return result


if __name__ == "__main__":
    run()
