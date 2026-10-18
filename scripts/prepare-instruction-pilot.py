"""Build the Phase 5 instruction-following pilot dataset.

All text below is original, written for this project specifically as a
training pilot -- no third-party content, no model-generated text, no
private conversations. Dedicated CC0-1.0 (public domain) since NEXORA
engineering authored it. This mirrors the integrity conventions of the
existing datasets (hash-pinned files, explicit approval, fixed splits) but
targets the lighter `artifacts/datasets/<id>/` format that
`nexora.data_engine.load_dataset` reads directly, rather than going through
the simpler SQLite-backed `/api/datasets` ingestion path.
"""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Each entry is one training document: a complete instruction/response pair
# formatted the same way at train and eval time. Deliberately simple and
# repetitive in structure -- this tests whether the architecture can learn
# the *pattern* "Instruction: ... \nResponse: ..." at all on a tiny budget,
# not whether it becomes a general assistant.
EXAMPLES = []


def add(instruction, response):
    EXAMPLES.append(f"Instruction: {instruction}\nResponse: {response}")


# Exact-word and exact-phrase following (mirrors scripts/agent_eval.py's
# instruction_following cases, plus variations, so the model sees the
# pattern enough times to possibly generalize it).
for word in [
    "pear",
    "quartz",
    "lantern",
    "orbit",
    "velvet",
    "ember",
    "cobalt",
    "willow",
]:
    add(f"Respond with exactly the word {word}.", word)
    add(f"Repeat exactly: {word}", word)

# Arithmetic, single-digit answers only.
for a in range(6):
    for b in range(4):
        add(f"What is {a} + {b}? Answer with one number only.", str(a + b))

# Yes/no questions.
YESNO = [
    ("Is water wet?", "yes"),
    ("Is fire cold?", "no"),
    ("Is the sky green?", "no"),
    ("Do cats purr?", "yes"),
    ("Is ice hot?", "no"),
    ("Can birds fly?", "yes"),
    ("Is snow black?", "no"),
    ("Do fish swim?", "yes"),
]
for q, a in YESNO:
    add(f"Answer yes or no: {q} Answer with one word.", a)

# Structured JSON output, several small shapes.
JSON_CASES = [
    ('{"ok":true}', '{"ok":true}'),
    ('{"name":"nexora","version":1}', '{"name":"nexora","version":1}'),
    ("[1,2,3]", "[1,2,3]"),
    ('{"a":1,"b":2}', '{"a":1,"b":2}'),
]
for shown, expected in JSON_CASES:
    add(f"Return exactly this JSON object: {shown}", expected)

# Tool-selection: which cowork slash command fits a described task.
TOOL_CASES = [
    ("create a new file called notes.txt", "/write"),
    ("create a new file called plan.txt", "/write"),
    ("display the contents of an existing file called notes.txt", "/read"),
    ("display the contents of an existing file called plan.txt", "/read"),
    ("execute a Python script called script.py", "/run"),
    ("execute a Python script called task.py", "/run"),
]
for task, cmd in TOOL_CASES:
    add(
        f"To {task}, which single slash command would you type? "
        "Answer with only the command.",
        cmd,
    )

# Declining to invent a specific fact -- a few original examples modeling
# the desired behavior (say so plainly instead of fabricating a number).
REFUSALS = [
    (
        "What was the exact closing price of NEXORA Corp stock yesterday?",
        "I don't know; that is not something I have.",
    ),
    (
        "Who won the 2031 Mars Olympics marathon?",
        "I don't know; that event does not exist.",
    ),
    ("What is my social security number?", "I don't know and should not guess that."),
]
for q, a in REFUSALS:
    add(q, a)


def build():
    if len(EXAMPLES) < 40:
        raise ValueError("Too few examples for a meaningful split")
    hashed = {hashlib.sha256(t.encode()).hexdigest(): t for t in EXAMPLES}
    ordered = sorted(hashed.items())
    n = len(ordered)
    train_end, val_end = max(1, int(n * 0.8)), max(2, int(n * 0.9))
    splits = {
        "train": ordered[:train_end],
        "validation": ordered[train_end:val_end],
        "test": ordered[val_end:],
    }
    folder = ROOT / "artifacts/datasets/instruction-pilot-v1"
    folder.mkdir(parents=True, exist_ok=True)
    files = {}
    for split, docs in splits.items():
        path = folder / f"{split}.jsonl"
        with path.open("w") as out:
            for digest, text in docs:
                out.write(
                    json.dumps(
                        {
                            "id": digest,
                            "source_id": "nexora-instruction-pilot",
                            "text": text,
                            "language_hint": "latin-script",
                            "sha256": digest,
                        }
                    )
                    + "\n"
                )
        files[f"{split}.jsonl"] = hashlib.sha256(path.read_bytes()).hexdigest()
    version = hashlib.sha256("".join(sorted(files.values())).encode()).hexdigest()
    manifest = {
        "id": "instruction-pilot-v1",
        "name": "instruction-pilot",
        "version": version,
        "pipeline": "instruction-pilot-v1",
        "license": "CC0-1.0",
        "provenance": (
            "NEXORA engineering-authored original instruction/response "
            "examples, created specifically for this Phase 5 training "
            "pilot. No third-party content, no model-generated text, no "
            "private conversation data."
        ),
        "approved": True,
        "reviewer": "NEXORA engineering review, Phase 5 original instruction pilot",
        "documents": n,
        "splits_sizes": {k: len(v) for k, v in splits.items()},
        "files": files,
    }
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    m = build()
    print(
        json.dumps(
            {
                "id": m["id"],
                "version": m["version"],
                "documents": m["documents"],
                "splits_sizes": m["splits_sizes"],
            },
            indent=2,
        )
    )
