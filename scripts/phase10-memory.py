"""Host namespace process sampling; service cgroup includes file cache, RSS may double count shared pages."""

import json, time, subprocess
from pathlib import Path
import psutil

root = Path(__file__).resolve().parent.parent
out = root / "docs/evidence/phase10/inference-memory.json"
start = time.monotonic()
samples = []
while time.monotonic() - start < 180:
    result = subprocess.run(
        ["flatpak-spawn", "--host", "ps", "-eo", "pid,ppid,rss,comm"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    rows = []
    for line in result.stdout.splitlines()[1:]:
        fields = line.split()
        if len(fields) == 4 and fields[3] in {"ollama", "runner"}:
            rows.append(
                {
                    "pid": int(fields[0]),
                    "ppid": int(fields[1]),
                    "rss_bytes": int(fields[2]) * 1024,
                    "name": fields[3],
                }
            )
    samples.append(
        {
            "seconds": time.monotonic() - start,
            "processes": rows,
            "available_bytes": psutil.virtual_memory().available,
            "swap_used": psutil.swap_memory().used,
        }
    )
    final = root / "docs/evidence/phase10/coding-final.json"
    if final.exists() and "summary" in json.loads(final.read_text()):
        break
    time.sleep(0.5)
measure = subprocess.run(
    [
        "flatpak-spawn",
        "--host",
        "systemctl",
        "--user",
        "show",
        "nexora-ollama",
        "-p",
        "MemoryMax",
        "-p",
        "MemoryPeak",
        "-p",
        "MemoryCurrent",
        "-p",
        "MemorySwapMax",
        "-p",
        "NRestarts",
    ],
    capture_output=True,
    text=True,
    timeout=5,
).stdout
out.write_text(
    json.dumps(
        {
            "samples": samples,
            "peak_sampled_process_tree_rss_bytes": max(
                (sum(p["rss_bytes"] for p in s["processes"]) for s in samples),
                default=None,
            ),
            "cgroup": measure,
            "limitations": "Sampling began after evaluation start; RSS sum may double count shared pages. Cgroup peak includes earlier service use and cache; neither is isolated model allocation.",
        },
        indent=2,
    )
    + "\n"
)
print(measure)
