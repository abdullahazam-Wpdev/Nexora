#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
export PATH="$PWD/.tools/node/bin:$PATH"
if test -x "$PWD/.tools/hopper/opt/hopper/bin/Hopper"; then
  export HOPPER_LAUNCHER_PATH="$PWD/.tools/hopper/opt/hopper/bin/Hopper"
fi
if command -v flatpak-spawn >/dev/null 2>&1; then
  exec flatpak-spawn --host env \
    "PATH=$PWD/.tools/xvfb/usr/bin:/usr/local/bin:/usr/bin:/bin" \
    "HOPPER_LAUNCHER_PATH=${HOPPER_LAUNCHER_PATH:-/opt/hopper/bin/Hopper}" \
    "$PWD/.tools/node/bin/node" \
    "$PWD/.tools/rea/node_modules/rea-agents/scripts/rea.mjs" "$@"
fi
exec .tools/rea/node_modules/.bin/rea "$@"
