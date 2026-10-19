"""Bounded Node/TypeScript acceptance in the existing rootless networkless image."""

import subprocess, tempfile, time, uuid
import shutil
from pathlib import Path
from nexora.config import ROOT
from nexora.cowork_sandbox import IMAGE, run_python


def run(root, profile, test):
    root = Path(root).resolve()
    # Flatpak /tmp differs from the host Podman namespace. Copy bounded staging
    # into the shared project directory; never follow symlinks out of scope.
    if not root.is_relative_to(ROOT):
        shared = ROOT / "artifacts/container-staging"
        shared.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=shared) as temporary:
            destination = Path(temporary)
            destination.chmod(0o755)
            files = list(root.rglob("*"))
            if len(files) > 32:
                raise ValueError("Sandbox staging file budget exceeded")
            for source in files:
                if source.is_symlink():
                    raise ValueError("Sandbox staging symlinks are unsupported")
                if source.is_file():
                    if source.stat().st_size > 16000:
                        raise ValueError("Sandbox staging source exceeds size limit")
                    target = destination / source.relative_to(root)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
            return run(destination, profile, test)
    if profile in {"python", "html"}:
        (root / "acceptance.py").write_text("import sys\nsys.path.insert(0, '/workspace')\n" + test)
        return run_python(root, root / "acceptance.py")
    if profile not in {"node", "typescript", "next-route"}:
        return "BLOCKED: no verified container runtime for " + profile
    if not (ROOT / ".tools/node-container-libs/ld-linux-x86-64.so.2").exists():
        return "BLOCKED: run scripts/prepare-node-sandbox.py"
    (root / "acceptance.cjs").write_text(test)
    name = "nexora-language-" + uuid.uuid4().hex[:12]
    command = [
        str(ROOT / "scripts/host-podman.sh"),
        "run",
        "--rm",
        "--pull=never",
        "--name",
        name,
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--pids-limit=32",
        "--memory=256m",
        "--memory-swap=256m",
        "--cpus=0.5",
        "--user=65534:65534",
        "--tmpfs=/tmp:rw,noexec,nosuid,size=8m",
        "-v",
        str(root) + ":/workspace:ro,z",
        "-v",
        str(ROOT / ".tools/node/bin/node") + ":/opt/node:ro,z",
        "-v",
        str(ROOT / ".tools/node-container-libs") + ":/opt/libs:ro,z",
        "-v",
        str(ROOT / "frontend/node_modules/typescript/lib") + ":/opt/typescript:ro,z",
        "--workdir=/workspace",
        IMAGE,
        "/opt/libs/ld-linux-x86-64.so.2",
        "--library-path",
        "/opt/libs",
        "/opt/node",
        "--max-old-space-size=128",
        "/workspace/acceptance.cjs",
    ]
    with tempfile.TemporaryFile() as output:
        process = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT)
        start = time.monotonic()
        reason = None
        try:
            while process.poll() is None:
                if time.monotonic() - start > 10:
                    reason = "Timeout"
                    break
                if output.tell() > 16384:
                    reason = "Output budget"
                    break
                time.sleep(0.05)
        finally:
            if process.poll() is None:
                process.kill()
            subprocess.run(
                [
                    str(ROOT / "scripts/host-podman.sh"),
                    "rm",
                    "--force",
                    "--time",
                    "0",
                    name,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
            )
            process.wait(timeout=5)
        output.seek(0)
        data = output.read(16384).decode(errors="replace")
    return (reason or f"Exit code: {process.returncode}") + "\n" + data
