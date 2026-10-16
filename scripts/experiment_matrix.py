"""Run a bounded, sequential matrix and retain machine-readable evidence."""

import json, subprocess, sys, time
from nexora.artifacts import atomic_json
from nexora.config import STORE, ROOT
from nexora.research import create_run


def main():
    manifests = list((STORE / "datasets").glob("python-tutorial-*/manifest.json"))
    if not manifests:
        raise RuntimeError("Acquire the reviewed dataset first")
    dataset = json.loads(manifests[0].read_text())["id"]
    specs = [
        (
            "phase2-tiny-benchmark",
            "tiny",
            {
                "steps": 20,
                "schedule_steps": 500,
                "eval_every": 20,
                "checkpoint_every": 20,
            },
        ),
        (
            "phase2-tiny-language",
            "tiny",
            {"steps": 400, "schedule_steps": 500, "learning_rate": 0.002},
        ),
        (
            "phase2-small-language",
            "small",
            {"steps": 400, "schedule_steps": 500, "learning_rate": 0.002},
        ),
        (
            "phase2-small-low-lr",
            "small",
            {"steps": 400, "schedule_steps": 500, "learning_rate": 0.001},
        ),
    ]
    evidence = ROOT / "docs/evidence/phase2"
    results = []
    for run_id, profile, options in specs:
        options.update(max_seconds=120, max_rss_mb=900, min_available_mb=500)
        if not (STORE / "runs" / run_id).exists():
            create_run(dataset, profile, options, run_id)
        command = [sys.executable, "-m", "nexora.research", "train", run_id]
        started = time.monotonic()
        log = STORE / "runs" / run_id / "console.log"
        with log.open("w") as f:
            process = subprocess.run(
                command, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT, timeout=150
            )
        result = json.loads((STORE / "runs" / run_id / "result.json").read_text())
        results.append(
            {
                "id": run_id,
                "command": command,
                "exit_code": process.returncode,
                "elapsed": time.monotonic() - started,
                "result": result,
            }
        )
        atomic_json(evidence / "experiment-matrix.json", results)
        print(
            run_id,
            result["status"],
            result.get("validation"),
            result.get("benchmark"),
            flush=True,
        )
        if process.returncode:
            print(log.read_text()[-1200:], flush=True)
    return results


if __name__ == "__main__":
    main()
