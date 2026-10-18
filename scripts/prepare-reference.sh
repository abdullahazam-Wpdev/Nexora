#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
.venv/bin/python scripts/download_reference.py
.venv/bin/python - <<'PY'
import hashlib, os, shutil, tempfile
from pathlib import Path
digest = '8030f04528538d47bda434f6f0bdf3952c40a58123e4d5e755332f23731a8684'
source = Path('.tools/downloads/smollm2-135m-q4_K_M.gguf')
with source.open('rb') as f:
    assert hashlib.file_digest(f, 'sha256').hexdigest() == digest
blobs = Path('artifacts/reference-models/ollama/blobs')
blobs.mkdir(parents=True, exist_ok=True)
with tempfile.NamedTemporaryFile(dir=blobs, delete=False) as staging:
    with source.open('rb') as f:
        shutil.copyfileobj(f, staging)
    name = staging.name
os.replace(name, blobs / ('sha256-' + digest))
PY
if ! curl -fsS --max-time 2 http://127.0.0.1:11434/api/version >/dev/null 2>&1; then
  ./scripts/ollama.sh start
fi
curl -fsS --retry 5 --retry-connrefused --retry-delay 1 --max-time 5 \
  http://127.0.0.1:11434/api/version
./scripts/ollama.sh pull
