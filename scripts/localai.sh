#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
root=$(pwd)
case "${1:-start}" in
  stop) exec flatpak-spawn --host /usr/bin/systemctl --user stop nexora-localai ;;
  version) exec env -u DEBUG .tools/localai/local-ai --version ;;
  start)
    if flatpak-spawn --host /usr/bin/systemctl --user is-active --quiet nexora-ollama; then
      scripts/ollama.sh stop
    fi
    mkdir -p artifacts/localai/models artifacts/localai/backends artifacts/localai/data
    if command -v flatpak-spawn >/dev/null 2>&1; then
      set -- flatpak-spawn --host /usr/bin/systemd-run --user --collect --unit=nexora-localai --property=MemoryMax=900M --property=MemorySwapMax=0 --property=CPUQuota=200% /usr/bin/env -u DEBUG "$root/.tools/localai/local-ai"
    else
      set -- env -u DEBUG "$root/.tools/localai/local-ai"
    fi
    exec "$@" run --address=127.0.0.1:8080 --models-path="$root/artifacts/localai/models" --backends-path="$root/artifacts/localai/backends" --data-path="$root/artifacts/localai/data" --threads=2 --context-size=512 --max-active-backends=1 --disable-web-ui --disable-mcp --disable-agents --disable-local-ai-assistant --disable-runtime-settings --disable-gallery-endpoint --autoload-galleries=false --autoload-backend-galleries=false --enable-watchdog-idle --watchdog-idle-timeout=15s --enable-watchdog-busy --watchdog-busy-timeout=45s ;;
  *) echo 'Usage: scripts/localai.sh [start|version]'; exit 2 ;;
esac
