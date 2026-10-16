"""Real abrupt-worker interruption and checkpoint recovery in an isolated project store."""

import json, os, shutil, subprocess, sys, time, uuid
from nexora.config import STORE, ROOT
from nexora.research import create_run, train_run, verify_checkpoint
from nexora.artifacts import atomic_json, sha256
from nexora import jobs

store = STORE / "phase3-recovery"
store.mkdir(exist_ok=True)
source = next((STORE / "datasets").glob("python-tutorial-*/manifest.json"))
dataset = json.loads(source.read_text())["id"]
dest = store / "datasets" / dataset
if not dest.exists():
    shutil.copytree(source.parent, dest)
run_id = "interruption-" + uuid.uuid4().hex[:8]
c = {
    "steps": 2000,
    "schedule_steps": 2000,
    "batch_size": 2,
    "accumulation": 1,
    "eval_every": 100,
    "checkpoint_every": 2,
    "max_seconds": 60,
    "architecture": {"dim": 32, "layers": 1, "heads": 2, "context": 32},
}
create_run(dataset, training=c, run_id=run_id, store=store)
folder = store / "runs" / run_id
cmd = [sys.executable, "-m", "nexora.research", "train", run_id]
with (folder / "console.log").open("w") as log:
    process = subprocess.Popen(
        cmd,
        cwd=ROOT,
        env={**os.environ, "NEXORA_STORAGE": str(store)},
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    try:
        deadline = time.monotonic() + 35
        while time.monotonic() < deadline:
            if (folder / "latest.json").exists():
                break
            if process.poll() is not None:
                raise RuntimeError((folder / "console.log").read_text()[-1000:])
            time.sleep(0.01)
        else:
            raise RuntimeError("No recovery checkpoint before timeout")
        observed = json.loads((folder / "latest.json").read_text())["step"]
        process.kill()
        exit_code = process.wait(timeout=10)
        state = jobs.status(store, run_id)
        assert state["status"] == "interrupted"
        info, cp = verify_checkpoint(folder)
        before = info["step"]
        digest = sha256(cp / "model.safetensors")
        recovered = train_run(run_id, resume=True, additional_steps=2, store=store)
        assert recovered["steps"] == before + 2 and recovered["status"] == "completed"
        assert sha256(cp / "model.safetensors") == digest
        atomic_json(
            ROOT / "docs/evidence/phase3/interruption-recovery.json",
            {
                "command": cmd,
                "killed_only_owned_worker_pid": process.pid,
                "exit_code": exit_code,
                "checkpoint_step_observed_before_kill": observed,
                "last_verified_step_after_kill": before,
                "status_after_kill": state["status"],
                "recovered_step": recovered["steps"],
                "original_checkpoint_unchanged": True,
                "new_checkpoint": recovered["checkpoint"],
                "note": "Actual SIGKILL interruption; exact next-update equivalence is separately covered by unit tests. Orphan staging files, if any, are retained for inspection.",
            },
        )
        print("Actual worker interruption and checkpoint recovery passed")
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
