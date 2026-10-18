#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
export PATH="$PWD/.tools/node/bin:$PATH"
mkdir -p .tools/rea
cp tooling/rea/package.json tooling/rea/package-lock.json .tools/rea/
npm ci --prefix .tools/rea --ignore-scripts --no-audit --no-fund
./scripts/rea.sh --version
if test -x .tools/xvfb/usr/bin/Xvfb; then
  .venv/bin/python scripts/patch-rea-xvfb.py
fi
