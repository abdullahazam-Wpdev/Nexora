"""Explicit Python execution in a rootless, networkless Podman container."""

import subprocess
import uuid
from nexora.config import ROOT

# Pinned during setup; no pull or package installation occurs on an API request.
IMAGE = "docker.io/library/python@sha256:2d9aefe2fef018a7eb2c13064c89c71929800fd2e5dccdbf52ea5da5bb8d929a"


def run_python(root, target):
    if target.suffix != ".py" or not target.is_file() or target.stat().st_size > 16000:
        raise ValueError("Choose an existing workspace .py file below 16 KB")
    wrapper = str(ROOT / "scripts/host-podman.sh")
    name = "nexora-task-" + uuid.uuid4().hex[:16]
    args = [
        wrapper,
        "run",
        "--pull=never",
        "--rm",
        "--name",
        name,
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--pids-limit=32",
        "--memory=96m",
        "--memory-swap=96m",
        "--cpus=0.5",
        "--user=65534:65534",
        "--tmpfs=/tmp:rw,noexec,nosuid,size=8m",
        "-v",
        f"{root.resolve()}:/workspace:ro,z",
        "--workdir=/workspace",
        IMAGE,
        "python",
        "-I",
        "-B",
        str("/workspace/" + target.relative_to(root.resolve()).as_posix()),
    ]
    # Limit output in the container before it reaches the API process.
    runner = "import runpy,sys,resource; resource.setrlimit(resource.RLIMIT_FSIZE,(16384,16384)); sys.argv=[sys.argv[1]]; runpy.run_path(sys.argv[0],run_name='__main__')"
    args[-4:] = [
        "python",
        "-I",
        "-B",
        "-c",
        runner,
        str("/workspace/" + target.relative_to(root.resolve()).as_posix()),
    ]
    # Use a temporary host file, bounded by terminating on excessive output below.
    import tempfile
    import time

    with tempfile.TemporaryFile() as output:
        process = subprocess.Popen(args, stdout=output, stderr=subprocess.STDOUT)
        started = time.monotonic()
        reason = None
        try:
            while process.poll() is None:
                if output.tell() > 16384:
                    reason = "Output limit reached"
                    break
                if time.monotonic() - started > 10:
                    reason = "Execution time limit reached"
                    break
                time.sleep(0.05)
        finally:
            if process.poll() is None:
                process.kill()
            subprocess.run(
                [wrapper, "rm", "--force", "--time", "0", name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
            )
            process.wait(timeout=5)
        output.seek(0)
        text = output.read(16384).decode(errors="replace")
    return (reason or f"Exit code: {process.returncode}") + "\n" + text
