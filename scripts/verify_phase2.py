"""Capture final command output and exit codes without altering training artifacts."""

import json, os, subprocess, sys, time
from pathlib import Path

out = Path("docs/evidence/phase2/final")
out.mkdir(parents=True, exist_ok=True)
env = {
    **os.environ,
    "PATH": str(Path(".tools/node/bin").resolve()) + ":" + os.environ["PATH"],
}
commands = [
    ("pytest", [sys.executable, "-m", "pytest", "-q"]),
    (
        "ruff",
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "nexora",
            "tests",
            "scripts",
            "--select",
            "F",
        ],
    ),
    ("typecheck", ["npm", "--prefix", "frontend", "run", "typecheck"]),
    ("build", ["npm", "--prefix", "frontend", "run", "build"]),
    ("npm-audit", ["npm", "--prefix", "frontend", "audit", "--json"]),
    ("pip-check", [sys.executable, "-m", "pip", "check"]),
    ("pip-audit", [sys.executable, "-m", "pip_audit", "--format", "json"]),
    (
        "browser",
        [
            sys.executable,
            "-c",
            "s=open('scripts/browser_qa.py').read().replace('Path(\"docs/evidence\")','Path(\"docs/evidence/phase2/final/browser\")');exec(compile(s,'scripts/browser_qa.py','exec'))",
        ],
    ),
]
results = []
for name, command in commands:
    begin = time.monotonic()
    try:
        p = subprocess.run(
            command, env=env, text=True, capture_output=True, timeout=180
        )
        r = {
            "name": name,
            "command": command,
            "exit_code": p.returncode,
            "stdout": p.stdout,
            "stderr": p.stderr,
            "seconds": time.monotonic() - begin,
        }
    except subprocess.TimeoutExpired:
        r = {"name": name, "command": command, "exit_code": 124, "error": "timeout"}
    (out / (name + ".json")).write_text(json.dumps(r, indent=2))
    results.append(r)
    print(name, r["exit_code"], flush=True)
(out / "summary.json").write_text(json.dumps(results, indent=2))
if any(r["exit_code"] for r in results):
    sys.exit(1)
