#!/usr/bin/env python3
"""Snapshot already-reviewed source clones; never install their listed services."""

import hashlib
import json
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parent.parent
rows = []
for name, url, license_name in [
    ("public-apis", "https://github.com/public-apis/public-apis", "MIT"),
    (
        "awesome-free-models",
        "https://github.com/12britz/awesome-free-models",
        "CC0-1.0",
    ),
]:
    source = root / "artifacts/vendor-src" / name
    target = root / "catalogs" / name
    target.mkdir(parents=True, exist_ok=True)
    commit = subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", "HEAD"], text=True
    ).strip()
    hashes = {}
    for filename in ["README.md", "LICENSE"]:
        content = (source / filename).read_bytes()
        (target / filename).write_bytes(content)
        hashes[filename] = hashlib.sha256(content).hexdigest()
    rows.append(
        dict(
            id=name,
            url=url,
            revision=commit,
            license=license_name,
            hashes=hashes,
            training_approved=False,
        )
    )
(root / "catalogs/manifest.json").write_text(json.dumps(rows, indent=2) + "\n")
