"""Copy existing Node loader/libraries for the pinned musl container; no download."""

import hashlib, json, re, shutil, subprocess
from pathlib import Path

root = Path(__file__).resolve().parent.parent
out = root / ".tools/node-container-libs"
out.mkdir(exist_ok=True)
libs = subprocess.check_output(["ldd", str(root / ".tools/node/bin/node")], text=True)
records = []
for value in re.findall(r"(?:=>\s*)?(/[^\s()]+)", libs):
    p = Path(value)
    if p.is_file():
        target = out / p.name
        shutil.copyfile(p, target)
        records.append(
            {"name": p.name, "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}
        )
(out / "ld-linux-x86-64.so.2").chmod(0o755)
(root / "docs/evidence/phase9/node-runtime.json").write_text(
    json.dumps(
        {
            "node_sha256": hashlib.sha256(
                (root / ".tools/node/bin/node").read_bytes()
            ).hexdigest(),
            "libraries": records,
            "distribution": "Local runtime copies only; not redistributed in Git",
        },
        indent=2,
    )
    + "\n"
)
