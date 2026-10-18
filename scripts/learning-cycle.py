#!/usr/bin/env python3
"""Bounded daily source discovery. New revisions require review, not automatic training."""

import hashlib
import json
import os
import fcntl
from contextlib import contextmanager
import time
from pathlib import Path
from urllib.request import Request, urlopen

root = Path(__file__).resolve().parent.parent
STORE = Path(os.environ.get("NEXORA_STORAGE", str(root / "artifacts"))).resolve()


@contextmanager
def lock(path):
    with open(path, "a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def atomic_json(path, value):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, indent=2))
    temp.replace(path)


SOURCES = [
    ("localai", "https://api.github.com/repos/mudler/LocalAI/commits?per_page=1"),
    (
        "public-apis",
        "https://api.github.com/repos/public-apis/public-apis/commits?per_page=1",
    ),
    (
        "awesome-free-models",
        "https://api.github.com/repos/12britz/awesome-free-models/commits?per_page=1",
    ),
]


def main():
    folder = STORE / "learning"
    folder.mkdir(exist_ok=True)
    result = {
        "timestamp": time.time(),
        "training_started": False,
        "policy": "Revision discovery only. License, provenance and evaluation review required before ingestion.",
        "sources": [],
    }
    with lock(folder / ".cycle.lock"):
        for name, url in SOURCES:
            row = {"id": name, "url": url, "training_approved": False}
            try:
                req = Request(
                    url,
                    headers={
                        "User-Agent": "Nexora-Research/0.1 (https://github.com/abdullahazam-Wpdev/Nexora)"
                    },
                )
                with urlopen(req, timeout=15) as response:
                    raw = response.read(262145)
                if len(raw) > 262144:
                    raise ValueError("Source exceeds 256 KB budget")
                payload = json.loads(raw)
                row.update(
                    revision=payload[0]["sha"],
                    sha256=hashlib.sha256(raw).hexdigest(),
                    status="candidate-needs-review",
                )
            except Exception as exc:
                row.update(status="error", error=type(exc).__name__)
            result["sources"].append(row)
        atomic_json(folder / "latest.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
