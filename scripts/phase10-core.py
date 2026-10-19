"""Two bounded random-init data-quality trials; disjoint values, common held-out test."""

import sys, json, hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nexora.instruction_pilot import run
from nexora.artifacts import atomic_json


def dataset(diverse):
    splits = {k: [] for k in ["train", "validation", "test"]}
    # Values are split by range, not merely prompt-prefix paraphrases.
    for split, values in [
        ("train", range(2, 14)),
        ("validation", range(20, 23)),
        ("test", range(31, 35)),
    ]:
        for n in values:
            rows = [
                ("Reply exactly " + str(n) + ".", str(n), "instruction"),
                (
                    "Write Python double" + str(n) + "(x) returning x*2.",
                    "def double" + str(n) + "(x):\n    return x*2",
                    "instruction",
                ),
                (
                    "Calculator returned " + str(n) + ". Give only its value.",
                    str(n),
                    "instruction",
                ),
                (
                    "Previous answer wrong. Verified value " + str(n) + ". Correct it.",
                    str(n),
                    "instruction",
                ),
                (
                    "User: Remember code "
                    + str(n)
                    + ".\nAssistant: Recorded.\nUser: Return that code only.",
                    str(n),
                    "instruction",
                ),
                (
                    "Owner has not approved publishing report " + str(n) + ".",
                    "Publishing requires owner approval.",
                    "instruction",
                ),
                (
                    "Calculate " + str(n) + "+1 using the calculator tool.",
                    json.dumps(
                        {
                            "tool": "calculator",
                            "arguments": {"expression": str(n) + "+1"},
                        },
                        separators=(",", ":"),
                    ),
                    "tool",
                ),
                (
                    "Read registered file item"
                    + str(n)
                    + ".py; propose the read tool.",
                    json.dumps(
                        {
                            "tool": "read_file",
                            "arguments": {"path": "item" + str(n) + ".py"},
                        },
                        separators=(",", ":"),
                    ),
                    "tool",
                ),
            ]
            if split == "train" and not diverse:
                # Same count/steps but repeated narrow values: quality/coverage ablation.
                rows = [
                    (p.replace(str(n), "2"), r.replace(str(n), "2"), k)
                    for p, r, k in rows
                ]
            for prompt, response, kind in rows:
                splits[split].append(
                    {
                        "prompt": prompt,
                        "response": response,
                        "kind": kind,
                        "split": split,
                        "license": "CC0-1.0",
                        "source_id": hashlib.sha256(
                            (prompt + response).encode()
                        ).hexdigest(),
                        "provenance": "Original deterministic Phase10 project fixture; owner-authorized bounded research; no private chats or external weights",
                        "training_approved": True,
                        "version": "phase10-v1",
                    }
                )
    # Exact dedup required: repeat narrow records rather than pretending unique data.
    for split, rows in splits.items():
        seen = set()
        splits[split] = [
            r for r in rows if not (r["source_id"] in seen or seen.add(r["source_id"]))
        ]
    sets = [{r["prompt"] for r in splits[s]} for s in splits]
    assert not sets[0] & sets[1] and not sets[0] & sets[2] and not sets[1] & sets[2]
    return splits


if __name__ == "__main__":
    report = {
        "experiments": [],
        "comparison": "Same random initialization seed, architecture dimensions, optimizer, 80 steps; tokenizers independently trained on training only. Losses across tokenizers are not directly comparable. Exact/schema scores use identical untouched test prompts. Synthetic family overlap remains.",
    }
    for label, diverse in [("narrow", False), ("diverse", True)]:
        result = run(
            "phase10-" + label + "-80",
            steps=80,
            corpus_data=dataset(diverse),
            evidence_phase="phase10",
        )
        result["semantic_tool_exact"] = sum(
            json.loads(r["expected"]) == json.loads(r["generated"])
            for r in result["records"]
            if r["kind"] == "tool" and r["schema_valid"]
        )
        report["experiments"].append(result)
        atomic_json(ROOT / "docs/evidence/phase10/core-comparison.json", report)
    print(
        [
            (r["id"], r["tool_correct"], r["instruction_exact"])
            for r in report["experiments"]
        ]
    )
