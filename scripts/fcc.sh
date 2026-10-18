#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
root=$(pwd)
host() {
  if command -v flatpak-spawn >/dev/null 2>&1; then flatpak-spawn --host "$@"; else "$@"; fi
}
case "${1:-status}" in
  start) host systemd-run --user --collect --unit=nexora-fcc --property=WorkingDirectory="$root" --property=MemoryMax=384M --property=MemorySwapMax=0 --property=CPUQuota=100% --property=TasksMax=96 "$root/.tools/fcc-venv/bin/python" "$root/scripts/fcc-sidecar.py" ;;
  stop) host systemctl --user stop nexora-fcc ;;
  status) host systemctl --user status nexora-fcc --no-pager ;;
  *) echo 'Usage: scripts/fcc.sh start|stop|status'; exit 2 ;;
esac
