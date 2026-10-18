#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
export OLLAMA_HOST=127.0.0.1:11434
ollama_binary="$PWD/.tools/ollama-fedora/usr/bin/ollama"
host() {
  if command -v flatpak-spawn >/dev/null 2>&1; then
    flatpak-spawn --host "$@"
  else
    "$@"
  fi
}
case "${1:-status}" in
  start)
    test -x "$ollama_binary"
    mkdir -p artifacts/reference-models/ollama
    host systemd-run --user --unit=nexora-ollama --collect \
      --property=MemoryMax=900M --property=MemorySwapMax=0 \
      --property=CPUQuota=200% --property=TasksMax=128 \
      --setenv=OLLAMA_HOST=127.0.0.1:11434 \
      --setenv="OLLAMA_MODELS=$PWD/artifacts/reference-models/ollama" \
      --setenv=OLLAMA_NO_CLOUD=1 --setenv=OLLAMA_NUM_PARALLEL=1 \
      --setenv=OLLAMA_NOPRUNE=1 \
      --setenv=OLLAMA_MAX_LOADED_MODELS=1 --setenv=OLLAMA_MAX_QUEUE=1 \
      --setenv=OLLAMA_CONTEXT_LENGTH=512 --setenv=OLLAMA_KEEP_ALIVE=0 \
      --setenv=OLLAMA_VULKAN=0 --setenv=CUDA_VISIBLE_DEVICES=-1 \
      --setenv="OLLAMA_LIBRARY_PATH=$PWD/.tools/ollama-fedora/usr/lib/ollama" \
      --setenv=OMP_NUM_THREADS=2 \
      "$ollama_binary" serve
    ;;
  stop) host systemctl --user stop nexora-ollama ;;
  status) host systemctl --user status nexora-ollama --no-pager ;;
  pull) host "$ollama_binary" pull smollm2:135m-instruct-q4_K_M ;;
  list) host "$ollama_binary" list ;;
  *) echo 'Usage: scripts/ollama.sh start|stop|status|pull|list' >&2; exit 2 ;;
esac
