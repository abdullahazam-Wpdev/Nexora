"""Benchmark the preserved original arithmetic runner without modifying its checkpoint."""

import contextlib, time
from pathlib import Path
import psutil
from nexora import train
from nexora.config import STORE
from nexora.artifacts import atomic_json

folder = STORE / "legacy-benchmark"
folder.mkdir(exist_ok=True)
train.STORE = folder
started = time.monotonic()
cpu_start = sum(psutil.Process().cpu_times()[:2])
with (folder / "console.log").open("w") as log, contextlib.redirect_stdout(log):
    result = train.run(20)
elapsed = time.monotonic() - started
atomic_json(
    Path("docs/evidence/phase2/legacy-benchmark.json"),
    {
        "steps": 20,
        "tokens": 20 * 4 * 64 * 2,
        "end_to_end_seconds": elapsed,
        "end_to_end_tokens_per_second": 20 * 4 * 64 * 2 / elapsed,
        "cpu_seconds": sum(psutil.Process().cpu_times()[:2]) - cpu_start,
        "rss_mb": psutil.Process().memory_info().rss / 1024**2,
        "warning": "Includes tokenizer, evaluation and checkpoint time. Arithmetic fixture differs from language corpus; not a controlled language-quality comparison.",
        "result": result,
    },
)
print("Legacy benchmark recorded")
