"""Reproducible small authored fixture corpus; no network/private conversation input."""

import hashlib
from pathlib import Path
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nexora.data_engine import SECRET
from nexora.artifacts import atomic_json
from tokenizers import Tokenizer

SOURCES = {
    "general": [
        "A solar panel converts incident sunlight into electrical energy. Output depends on illumination and installation angle.",
        "Freshwater wetlands shelter amphibians and filter sediments carried by seasonal rainfall.",
        "Public libraries lend books and provide quiet spaces for independent study.",
    ],
    "code": [
        "def add(a, b):\n    return a + b\n",
        "def reverse_word(word):\n    return word[::-1]\n",
        "def is_positive(value):\n    return value > 0\n",
    ],
    "instructions": [
        "Task: Reply using one lowercase fruit name. Answer: pear",
        "Request: Sort these integers ascending: 9, 2, 5. Response: 2, 5, 9",
        'Instruction: Return a JSON boolean flag. Completion: {"ready":true}',
    ],
    "tool_calling": [
        'Task: Compute 17 multiplied by 23. Action: {"tool":"calculator","arguments":{"expression":"17*23"}}',
        'Goal: Inspect an approved source module. Tool request: {"tool":"read_file","arguments":{"path":"parser.py"}}',
        'Need: Locate current public references. Selected operation: {"tool":"search","arguments":{"query":"Python documentation"}}',
    ],
    "error_recovery": [
        "Observation: A permitted fetch timed out. Recovery: retry that source once, then report unavailable.",
        "Failure: Acceptance assertion did not pass. Next: preserve the original file, revise only the staged candidate and run checks again.",
        "Error: Model service rejected credentials. Response: stop and report missing access; never substitute an unapproved paid backend.",
    ],
    "planning": [
        "Goal: Repair a pure Python addition bug. Plan: inspect the source; propose a staged diff; run assertions; request exact approval.",
        "Objective: Compare two public documents. Steps: collect references, retain quotations with provenance, identify agreement and note uncertainty.",
        "Task: Verify a disposable browser form. Sequence: approve the fixed plan, enter test data, click preview, assert the greeting and retain a screenshot.",
    ],
}


def build():
    tokenizer = Tokenizer.from_file(
        str(ROOT / "artifacts/runs/phase2-small-language/tokenizer.json")
    )
    records = []
    seen = set()
    grams = {s: set() for s in ["train", "validation", "test"]}
    for kind, texts in SOURCES.items():
        for index, text in enumerate(texts):
            canonical = unicodedata.normalize("NFKC", text).strip()
            if len(canonical) < 12 or SECRET.search(canonical):
                raise ValueError("Quality/private-data rejection")
            digest = hashlib.sha256(canonical.encode()).hexdigest()
            if digest in seen:
                raise ValueError("Duplicate source")
            seen.add(digest)
            split = ["train", "validation", "test"][index]
            words = re.findall(r"\w+", canonical.lower())
            grams[split].update(tuple(words[i : i + 5]) for i in range(len(words) - 4))
            records.append(
                {
                    "source_id": kind + "-" + str(index),
                    "kind": kind,
                    "split": split,
                    "text": canonical,
                    "sha256": digest,
                    "tokens": len(tokenizer.encode(canonical).ids),
                    "license": "CC0-1.0",
                    "provenance": "Project-authored synthetic fixture; not scraped/private/model-service output",
                }
            )
    contamination = {
        a + "-" + b: len(grams[a] & grams[b])
        for a, b in [("train", "validation"), ("train", "test"), ("validation", "test")]
    }
    if any(contamination.values()):
        raise ValueError("Cross-split exact five-word contamination detected")
    result = {
        "schema": "nexora-authored-fixture-corpus-v1",
        "training_approved": True,
        "warning": "18 tiny sources for pipeline tests; inadequate for foundation pretraining. Not used by Phase 8 tool-SFT comparisons.",
        "contamination": contamination,
        "records": records,
        "tokens": sum(r["tokens"] for r in records),
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    atomic_json(ROOT / "docs/evidence/phase8/authored-data-manifest.json", result)
    print(
        "Authored sources:",
        len(records),
        "tokens:",
        result["tokens"],
        "contamination:",
        contamination,
    )
    return result


if __name__ == "__main__":
    build()
