"""Measure the Phase 2 checkpoint, including monitor/evaluation bottlenecks."""

import json, time, statistics
import torch, psutil
from safetensors.torch import load_file, save_file
from tokenizers import Tokenizer
from nexora.research import (
    Config,
    Core,
    TrainConfig,
    Monitor,
    evaluate,
    _mapped_tokens,
    optimizer_for,
)
from nexora.config import STORE
from nexora.artifacts import atomic_json


def main():
    torch.set_num_threads(2)
    folder = STORE / "runs/phase2-small-language"
    run = json.loads((folder / "result.json").read_text())
    cp = (
        folder
        / "checkpoints"
        / json.loads((folder / "latest.json").read_text())["directory"]
    )
    m = Core(Config(**run["config"]))
    m.load_state_dict(load_file(str(cp / "model.safetensors")))
    arrays = _mapped_tokens(folder, json.loads((folder / "tokens.json").read_text()))
    c = TrainConfig(**run["training"])
    monitor = Monitor(c, STORE)
    cpu = psutil.Process()
    startcpu = sum(cpu.cpu_times()[:2])
    started = time.monotonic()
    values = []
    for _ in range(25):
        t = time.monotonic()
        monitor.check()
        values.append(time.monotonic() - t)
    evals = {}
    for mode in ["unmonitored", "monitored", "monitored-batched"]:
        t = time.monotonic()
        r = evaluate(
            m,
            arrays["validation"],
            m.config.context,
            monitor if mode != "unmonitored" else None,
            batch_size=8 if mode == "monitored-batched" else 1,
        )
        evals[mode] = {"seconds": time.monotonic() - t, "metrics": r}
    opt = optimizer_for(m, c)
    x = torch.randint(0, m.config.vocab_size, (4, 128))
    y = torch.randint(0, m.config.vocab_size, (4, 128))
    durations = []
    for i in range(13):
        t = time.monotonic()
        opt.zero_grad(set_to_none=True)
        for _ in range(2):
            loss = (
                torch.nn.functional.cross_entropy(m(x).flatten(0, 1), y.flatten()) / 2
            )
            loss.backward()
        torch.nn.utils.clip_grad_norm_(m.parameters(), 1)
        opt.step()
        if i >= 3:
            durations.append(time.monotonic() - t)
    # Reload the real weights after the synthetic timing updates.
    m.load_state_dict(load_file(str(cp / "model.safetensors")))
    tok = Tokenizer.from_file(str(folder / "tokenizer.json"))
    ids = torch.tensor([tok.encode("Python is").ids])
    inference = []
    for _ in range(5):
        t = time.monotonic()
        m.generate(ids, 64)
        inference.append(time.monotonic() - t)
    t = time.monotonic()
    load_file(str(cp / "model.safetensors"))
    load_seconds = time.monotonic() - t
    scratch = STORE / "benchmarks" / "phase3-save"
    scratch.mkdir(parents=True, exist_ok=True)
    saves = []
    for _ in range(3):
        t = time.monotonic()
        save_file(
            {k: v.detach().contiguous().clone() for k, v in m.state_dict().items()},
            str(scratch / "weights.safetensors"),
        )
        torch.save(
            {"model": m.state_dict(), "optimizer": opt.state_dict()},
            scratch / "optimizer.pt",
        )
        saves.append(time.monotonic() - t)
    result = {
        "model": "phase2-small-language",
        "parameters": run["parameters"],
        "monitor_median_seconds": statistics.median(values),
        "evaluation": evals,
        "training_step_median_seconds": statistics.median(durations),
        "training_tokens_per_second": 1024 / statistics.median(durations),
        "training_seconds_per_million_tokens": 1e6
        * statistics.median(durations)
        / 1024,
        "warm_inference_tokens_per_second": 64 / statistics.median(inference),
        "warm_inference_median_seconds_64_tokens": statistics.median(inference),
        "checkpoint_read_seconds": load_seconds,
        "checkpoint_buffered_save_median_seconds": statistics.median(saves),
        "checkpoint_bytes": sum(p.stat().st_size for p in cp.iterdir()),
        "rss_mb": cpu.memory_info().rss / 1024**2,
        "resources": monitor.metrics(),
        "cpu_percent_one_core": 100
        * (sum(cpu.cpu_times()[:2]) - startcpu)
        / (time.monotonic() - started),
        "notes": "Synthetic fixed batches time kernels only; no training result is published. Original checkpoint is read-only. Warm inference excludes model verification/loading and has no KV cache.",
    }
    atomic_json("docs/evidence/phase3/optimized-performance.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
