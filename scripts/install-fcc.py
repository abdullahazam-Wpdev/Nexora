#!/usr/bin/env python3
"""Install the audited user ZIP into a separate environment; no client auto-config."""

import hashlib
import stat
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = Path("/home/abdullah/Downloads/free-claude-code-main.zip")
DIGEST = "1368b42cecc2cb511c482e0721143e59db7ca0cde93df01f6a33e919187cf267"
if hashlib.sha256(ARCHIVE.read_bytes()).hexdigest() != DIGEST:
    raise SystemExit("Archive changed; repeat source and license review")
folder = ROOT / "artifacts/vendor-src/free-claude-code-zip"
folder.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(ARCHIVE) as archive:
    if (
        len(archive.infolist()) > 2000
        or sum(x.file_size for x in archive.infolist()) > 25_000_000
    ):
        raise SystemExit("Archive exceeds review budget")
    for entry in archive.infolist():
        rel = Path(entry.filename)
        if (
            rel.is_absolute()
            or ".." in rel.parts
            or stat.S_ISLNK(entry.external_attr >> 16)
        ):
            raise SystemExit("Unsafe archive entry")
        target = folder / rel
        if not target.resolve().is_relative_to(folder.resolve()):
            raise SystemExit("Unsafe extraction target")
        if entry.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            content = archive.read(entry)
            if target.exists() and target.read_bytes() != content:
                raise SystemExit(
                    "Existing extracted source changed; preserve and review it"
                )
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
source = folder / "free-claude-code-main"
uv = str(ROOT / ".venv/bin/uv")
subprocess.run(
    [
        uv,
        "python",
        "install",
        "3.14.7",
        "--install-dir",
        str(ROOT / ".tools/fcc-python"),
    ],
    check=True,
)
python = ROOT / ".tools/fcc-python/cpython-3.14.7-linux-x86_64-gnu/bin/python3.14"
env = ROOT / ".tools/fcc-venv"
if not env.exists():
    subprocess.run([uv, "venv", "--python", str(python), str(env)], check=True)
# ZIP lacks VCS metadata. An explicit local import commit supplies packaging
# metadata; it is not an upstream release/version claim.
if not (source / ".git").exists():
    subprocess.run(["git", "init", "-q", str(source)], check=True)
    subprocess.run(["git", "-C", str(source), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(source),
            "-c",
            "user.name=Nexora local import",
            "-c",
            "user.email=local-import@localhost",
            "commit",
            "-qm",
            "Import audited user ZIP " + DIGEST,
        ],
        check=True,
    )
subprocess.run(
    [
        uv,
        "pip",
        "install",
        "--python",
        str(env / "bin/python"),
        "-r",
        str(ROOT / "tooling/fcc/requirements.lock"),
    ],
    check=True,
)
subprocess.run(
    [
        uv,
        "pip",
        "install",
        "--python",
        str(env / "bin/python"),
        "--no-deps",
        str(source),
    ],
    check=True,
)
subprocess.run([uv, "pip", "check", "--python", str(env / "bin/python")], check=True)
print("Installed isolated FCC. Run .tools/fcc-venv/bin/python scripts/fcc-sidecar.py")
