#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
export PATH="$PWD/.tools/node/bin:$PATH"
case "${1:-}" in
  api) exec .venv/bin/python -m uvicorn nexora.api:app --host 127.0.0.1 --port 8000 ;;
  ui) cd frontend; exec npm run start -- --port 3001 ;;
  *) echo 'Run in separate terminals: scripts/start-local.sh api and scripts/start-local.sh ui'; exit 2 ;;
esac
