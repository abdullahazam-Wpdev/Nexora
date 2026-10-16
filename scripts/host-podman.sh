#!/bin/sh
set -eu
if command -v podman >/dev/null 2>&1; then
  exec podman "$@"
fi
if command -v flatpak-spawn >/dev/null 2>&1; then
  exec flatpak-spawn --host /usr/bin/podman "$@"
fi
echo 'Podman is unavailable; run in a Fedora host shell.' >&2
exit 127
