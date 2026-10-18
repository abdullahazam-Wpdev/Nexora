#!/usr/bin/env python3
"""A bounded, separately checkpointed next-token pilot on MIT LocalAI documentation."""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
from nexora.config import STORE
from nexora.data_engine import build_dataset
from nexora.research import create_run, train_run

parser = argparse.ArgumentParser()
parser.add_argument("--run-id", default="localai-docs-pilot-8")
args = parser.parse_args()

source = root / "artifacts/vendor-src/localai"
revision = subprocess.check_output(
    ["git", "-C", str(source), "rev-parse", "HEAD"], text=True
).strip()
license_text = (source / "LICENSE").read_text()
if not license_text.startswith("MIT License"):
    raise SystemExit("License changed; review required")
paths = [
    "README.md",
    "docs/content/overview.md",
    "docs/content/reference/architecture.md",
    "docs/content/reference/runtime-errors.md",
    "docs/content/getting-started/models.md",
    "docs/content/getting-started/customize-model.md",
]
documents = []
for name in paths:
    raw = (source / name).read_bytes()
    text = raw.decode()
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    paragraphs = [
        p.strip()
        for p in text.split("\n\n")
        if 100 <= len(p.strip()) <= 2000
        and not p.strip().startswith(("<", "{{", "---"))
    ]
    for text in paragraphs[:12]:
        documents.append(
            {
                "source_id": name,
                "url": f"https://github.com/mudler/LocalAI/blob/{revision}/{name}",
                "raw_sha256": hashlib.sha256(raw).hexdigest(),
                "text": text,
            }
        )
manifest = build_dataset(
    "localai-docs-pilot",
    documents,
    approved=True,
    license="MIT",
    provenance=f"MIT LocalAI documentation at {revision}; retained notice; repository documents, authorship not independently verified. No proprietary chat outputs. Separate source-level holdouts; pilot does not claim instruction ability.",
    notices=license_text,
    store=STORE,
)
print(
    json.dumps(
        {"dataset": manifest["id"], "documents": len(documents), "revision": revision}
    ),
    flush=True,
)
run = create_run(
    manifest["id"],
    "tiny",
    {
        "steps": 8,
        "schedule_steps": 8,
        "warmup_steps": 2,
        "batch_size": 2,
        "accumulation": 1,
        "eval_every": 8,
        "checkpoint_every": 8,
        "max_seconds": 40,
        "threads": 2,
    },
    run_id=args.run_id,
    store=STORE,
)
result = train_run(run["id"], store=STORE)
print(json.dumps(result, indent=2))
