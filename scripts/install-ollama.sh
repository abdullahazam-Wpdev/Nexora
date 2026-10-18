#!/bin/sh
# Fedora 44 CPU runtime, extracted locally; no system RPM transaction.
set -eu
cd "$(dirname "$0")/.."
mkdir -p .tools/downloads
package=.tools/downloads/ollama-0.12.11-4.fc44.x86_64.rpm
digest=f56508d8870255eae71b47f0cba6afa3cc5151457c79234503cbcecc8bb23f1c
host() {
  if command -v flatpak-spawn >/dev/null 2>&1; then
    flatpak-spawn --host "$@"
  else
    "$@"
  fi
}
if ! printf '%s  %s\n' "$digest" "$package" | sha256sum --check --status; then
  curl -fL --connect-timeout 15 --max-time 600 \
    https://dl.fedoraproject.org/pub/fedora/linux/releases/44/Everything/x86_64/os/Packages/o/ollama-0.12.11-4.fc44.x86_64.rpm \
    -o "$package.partial"
  printf '%s  %s\n' "$digest" "$package.partial" | sha256sum --check
  mv "$package.partial" "$package"
fi
host rpmkeys --checksig --verbose "$PWD/$package"
if test -d .tools/ollama-fedora; then
  echo 'Verified package; local extraction already exists. Stop the service before manually replacing it.'
  exit 0
fi
mkdir .tools/ollama-fedora-stage
host rpm2cpio "$PWD/$package" > .tools/ollama-fedora.cpio
(cd .tools/ollama-fedora-stage && cpio -idmu --quiet < ../ollama-fedora.cpio)
mv .tools/ollama-fedora-stage .tools/ollama-fedora
rm .tools/ollama-fedora.cpio
echo 'Installed. Run scripts/ollama.sh start, then scripts/ollama.sh pull.'
