"""Unprivileged rootless infrastructure verification; never prints passwords."""

import argparse, json, os, secrets, subprocess, sys, time
from pathlib import Path

root = Path(__file__).resolve().parent.parent
os.chdir(root)
evidence = root / "docs/evidence/phase2/infra"
evidence.mkdir(parents=True, exist_ok=True)
podman = str(root / "scripts/host-podman.sh")
records = []


def execute(args, check=True):
    p = subprocess.run(args, capture_output=True, text=True, timeout=180)
    r = {
        "command": args,
        "exit_code": p.returncode,
        "stdout": p.stdout,
        "stderr": p.stderr,
    }
    records.append(r)
    (evidence / "commands.json").write_text(json.dumps(records, indent=2))
    print(args[1:3], p.returncode, flush=True)
    if check and p.returncode:
        raise RuntimeError(p.stderr[-1000:])
    return p.stdout.strip()


p = argparse.ArgumentParser()
p.add_argument("action", choices=["up", "verify", "status"])
a = p.parse_args()
info = json.loads(execute([podman, "info", "--format", "json"]))
assert info["host"]["security"]["rootless"], "Rootless Podman is required"
secret = root / ".secrets/postgres_password"
if a.action == "up":
    secret.parent.mkdir(mode=0o700, exist_ok=True)
    if not secret.exists():
        fd = os.open(secret, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(secrets.token_urlsafe(32))
    secret.chmod(0o444)  # Parent stays 0700; container postgres UID needs read access.
    execute(
        [
            sys.executable,
            "-m",
            "podman_compose",
            "--podman-path",
            podman,
            "-p",
            "nexora",
            "-f",
            str(root / "compose.yaml"),
            "up",
            "-d",
        ]
    )
if a.action in {"up", "verify"}:
    for _ in range(20):
        rows = json.loads(execute([podman, "ps", "--format", "json"]))
        selected = [
            r
            for r in rows
            if r.get("Labels", {}).get("com.docker.compose.project") == "nexora"
            or r.get("Labels", {}).get("io.podman.compose.project") == "nexora"
        ]
        if len(selected) == 2 and all(
            "healthy" in r.get("Status", "").lower() for r in selected
        ):
            break
        time.sleep(2)
    else:
        raise RuntimeError("Container health checks did not become healthy")

    def find(service):
        return next(
            r["Id"]
            for r in selected
            if r.get("Labels", {}).get("com.docker.compose.service") == service
            or r.get("Labels", {}).get("io.podman.compose.service") == service
        )

    pg, redis = find("postgres"), find("redis")
    execute(
        [
            podman,
            "exec",
            pg,
            "psql",
            "-U",
            "nexora",
            "-d",
            "nexora",
            "-c",
            "CREATE TABLE IF NOT EXISTS nexora_infra_proof(id integer PRIMARY KEY, value text); INSERT INTO nexora_infra_proof VALUES(1,'persistent') ON CONFLICT(id) DO UPDATE SET value=EXCLUDED.value;",
        ]
    )
    execute(
        [podman, "exec", redis, "redis-cli", "SET", "nexora:infra:proof", "persistent"]
    )
    execute([podman, "restart", pg, redis])
    for _ in range(20):
        ready = (
            subprocess.run(
                [podman, "exec", pg, "pg_isready", "-U", "nexora"], capture_output=True
            ).returncode
            == 0
        )
        if ready:
            break
        time.sleep(1)
    value = execute(
        [
            podman,
            "exec",
            pg,
            "psql",
            "-U",
            "nexora",
            "-d",
            "nexora",
            "-tAc",
            "SELECT value FROM nexora_infra_proof WHERE id=1",
        ]
    )
    assert value == "persistent"
    assert (
        execute([podman, "exec", redis, "redis-cli", "GET", "nexora:infra:proof"])
        == "persistent"
    )
    execute([podman, "port", pg])
    execute([podman, "port", redis])
execute([podman, "ps", "--format", "json"])
print("Infrastructure verification complete", flush=True)
