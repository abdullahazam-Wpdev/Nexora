#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
.venv/bin/python scripts/download-localai.py
chmod +x .tools/localai/local-ai
mkdir -p artifacts/localai/models artifacts/localai/backends artifacts/localai/data
ln -sf ../../../.tools/downloads/smollm2-135m-q4_K_M.gguf artifacts/localai/models/smollm2.gguf
cp tooling/localai/smollm2.yaml artifacts/localai/models/
env -u DEBUG .tools/localai/local-ai backends install 'oci://quay.io/go-skynet/local-ai-backends@sha256:cc0eaf6d6db4c5c22b9e431e7d90b917906a2262add102da65f241b4cfe06bf7' llama-cpp llama-cpp --backends-path="$PWD/artifacts/localai/backends"
