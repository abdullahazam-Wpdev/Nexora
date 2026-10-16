#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
export PATH="$PWD/.tools/node/bin:$PATH"
.venv/bin/python -m pytest -q
npm --prefix frontend run typecheck
npm --prefix frontend run build
