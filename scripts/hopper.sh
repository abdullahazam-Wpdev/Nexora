#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
hopper_binary="$PWD/.tools/hopper/opt/hopper/bin/Hopper"
if command -v flatpak-spawn >/dev/null 2>&1; then
  exec flatpak-spawn --host "$hopper_binary" "$@"
fi
exec "$hopper_binary" "$@"
