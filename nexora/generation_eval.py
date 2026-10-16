"""Inspectable generation diagnostics; never reused as training data."""

import json
import re
from collections import Counter
from pathlib import Path
import torch
from safetensors.torch import load_file
from tokenizers import Tokenizer
from nexora.artifacts import atomic_json
from nexora.config import STORE
from nexora.data_engine import load_dataset
from nexora.model import Core, Config
from nexora.research import verify_checkpoint

INSTRUCTIONS = [
    {"prompt": "Respond with exactly the word pear:\n", "expected": "pear"},
    {"prompt": "What is 2 + 3? Answer with one digit only:\n", "expected": "5"},
    {
        "prompt": 'Return exactly this JSON object: {"ok":true}\n',
        "expected": '{"ok":true}',
    },
    {"prompt": "Repeat exactly: quartz\n", "expected": "quartz"},
]


def diagnostics(text, training):
    words = re.findall(r"\S+", text)
    triples = list(zip(words, words[1:], words[2:]))
    pairs = list(zip(words, words[1:]))
    counts = Counter(triples)
    # Bounded longest exact matching word span, not a semantic memorization detector.
    longest = 0
    for n in range(min(32, len(words)), 2, -1):
        if any(
            " ".join(words[i : i + n]) in training for i in range(len(words) - n + 1)
        ):
            longest = n
            break
    return {
        "words": len(words),
        "distinct_1": len(set(words)) / max(1, len(words)),
        "distinct_2": len(set(pairs)) / max(1, len(pairs)),
        "repeated_trigram_fraction": sum(max(0, n - 1) for n in counts.values())
        / max(1, len(triples)),
        "longest_exact_training_word_span_capped_32": longest,
        "exact_continuation_in_train": len(text) >= 40 and text in training,
    }


def evaluate_generation(run_id, store=None, checkpoint=None):
    store = Path(store or STORE)
    folder = store / "runs" / run_id
    r = json.loads((folder / "result.json").read_text())
    info, cp = verify_checkpoint(folder, checkpoint)
    torch.set_num_threads(2)
    m = Core(Config(**info["config"]))
    m.load_state_dict(load_file(str(cp / "model.safetensors")))
    m.eval()
    tok = Tokenizer.from_file(str(folder / "tokenizer.json"))
    _, docs = load_dataset(r["dataset_id"], store)
    training = "\n".join(" ".join(d["text"].split()) for d in docs["train"])

    def continuation(prompt, count=48):
        ids = tok.encode(prompt).ids or [0]
        result = m.generate(torch.tensor([ids]), count)[0].tolist()
        return tok.decode(result[len(ids) :], skip_special_tokens=False)

    examples = []
    for prompt in ["Python is", "The function returns", "A dictionary contains"]:
        text = continuation(prompt)
        examples.append(
            {
                "prompt": prompt,
                "continuation": text,
                "diagnostics": diagnostics(" ".join(text.split()), training),
            }
        )
    recall = []
    # Compare prefix completion of real train documents and validation documents.
    for split in ("train", "validation"):
        for d in docs[split][:3]:
            words = d["text"].split()
            if len(words) < 20:
                continue
            prefix = " ".join(words[:10])
            expected = " ".join(words[10:20])
            text = continuation(prefix, 32)
            recall.append(
                {
                    "split": split,
                    "source_id": d["source_id"],
                    "prefix": prefix,
                    "generated": text,
                    "expected_next_10_words": expected,
                    "exact_prefix_match": text.lstrip().startswith(expected),
                    "diagnostics": diagnostics(" ".join(text.split()), training),
                }
            )
    instruction = []
    for task in INSTRUCTIONS:
        text = continuation(task["prompt"], 16)
        instruction.append(
            {
                **task,
                "generated": text,
                "strict_success": text.strip() == task["expected"],
            }
        )
    return {
        "run_id": run_id,
        "checkpoint_step": info["step"],
        "decoding": "Deterministic greedy, no KV cache; fixed prompt/count protocol",
        "free_generation": examples,
        "prefix_completion": recall,
        "instruction_probes": instruction,
        "strict_instruction_successes": sum(x["strict_success"] for x in instruction),
        "instruction_probe_count": len(instruction),
        "limitation": "Four local formatting/arithmetic probes are not a reasoning benchmark. Exact-span overlap cannot establish or rule out semantic memorization. Diagnostic outputs are never ingested as training data.",
    }


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("run_id")
    p.add_argument("--output", required=True)
    a = p.parse_args()
    result = evaluate_generation(a.run_id)
    atomic_json(a.output, result)
    print("Generation diagnostic evidence written")
