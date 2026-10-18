"""Download explicitly approved NVIDIA reference weights for storage only."""

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DIGEST = "be5d9a656a51922f24f1f09a759cebb694e1f5d9728bf0ef9f8c972c5a0b5ef2"
SIZE = 2837072864
CHUNK = 8 * 1024 * 1024
PARTS = ROOT / ".tools/downloads/nvidia-nano4b-parts"
OUTPUT = ROOT / "artifacts/reference-models/nvidia/NVIDIA-Nemotron3-Nano-4B-Q4_K_M.gguf"
URL = 'https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF/resolve/ba223d14e45525f7fae81db77ea8cabeb2fc6c25/NVIDIA-Nemotron3-Nano-4B-Q4_K_M.gguf'


def fetch(index):
    path = PARTS / str(index)
    start = index * CHUNK
    end = min(SIZE, start + CHUNK)
    for attempt in range(3):
        offset = path.stat().st_size if path.exists() else 0
        if offset == end - start:
            return
        if offset > end - start:
            raise ValueError("Oversize cached part")
        begin = start + offset
        try:
            req = Request(URL + f"?download=true&range_start={begin}", headers={"Range": f"bytes={begin}-{end - 1}"})
            with urlopen(req, timeout=30) as response:
                expected = f"bytes {begin}-{end - 1}/{SIZE}"
                if (
                    response.status != 206
                    or response.headers.get("Content-Range") != expected
                ):
                    raise ValueError("Server did not honor the exact requested range")
                with path.open("ab") as out:
                    while begin < end:
                        block = response.read(min(65536, end - begin))
                        if not block:
                            raise ValueError("Truncated download")
                        out.write(block)
                        begin += len(block)
            print(f"Verified range length for part {index}", flush=True)
            return
        except (OSError, ValueError):
            if attempt == 2:
                raise


def main():
    started = time.monotonic()
    PARTS.mkdir(parents=True, exist_ok=True)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    if OUTPUT.exists():
        with OUTPUT.open("rb") as source:
            if hashlib.file_digest(source, "sha256").hexdigest() == DIGEST:
                print("Pinned NVIDIA reference already verified")
                return
    count = (SIZE + CHUNK - 1) // CHUNK
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(fetch, range(count)))
    staging = OUTPUT.with_suffix(".staging")
    digest = hashlib.sha256()
    with staging.open("wb") as out:
        for i in range(count):
            with (PARTS / str(i)).open("rb") as part:
                while block := part.read(1024 * 1024):
                    out.write(block)
                    digest.update(block)
    if staging.stat().st_size != SIZE or digest.hexdigest() != DIGEST:
        raise SystemExit("NVIDIA weight SHA-256 mismatch; blob not published")
    os.replace(staging, OUTPUT)
    record = {
        "status": "verified",
        "purpose": "storage-only; not loaded or selected",
        "revision": "ba223d14e45525f7fae81db77ea8cabeb2fc6c25",
        "sha256": DIGEST,
        "bytes": SIZE,
        "seconds": time.monotonic() - started,
        "path": str(OUTPUT),
    }
    (ROOT / "artifacts/nvidia-download.json").write_text(
        json.dumps(record, indent=2) + "\n"
    )
    print(json.dumps(record), flush=True)


if __name__ == "__main__":
    main()
