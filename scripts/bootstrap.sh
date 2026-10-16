#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
python3 -m venv .venv
.venv/bin/python -m pip install --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.lock
export PATH="$PWD/.tools/node/bin:$PATH"
command -v node >/dev/null || { echo 'Install Node 22+ in your user environment first.'; exit 1; }
npm --prefix frontend ci
npm --prefix frontend run build
