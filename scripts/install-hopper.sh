#!/bin/sh
# Official free demo; use only after accepting Hopper's vendor license.
# All extraction is user-local. No RPM transaction or desktop registration.
set -eu
cd "$(dirname "$0")/.."
host() {
  if command -v flatpak-spawn >/dev/null 2>&1; then
    flatpak-spawn --host "$@"
  else
    "$@"
  fi
}
mkdir -p .tools/downloads artifacts
archive=.tools/downloads/Hopper-6.6.0-Linux-demo.pkg.tar.xz
if ! printf '%s  %s\n' 609ff72b8caaf6e17c8c87c514b5d3b41e1040ddb9d48a14d4ba573d65c9aedb "$archive" | sha256sum --check --status; then
  curl --http1.1 -fL -A rea-installer --connect-timeout 15 --max-time 600 \
    https://www.hopperapp.com/downloader/public/Hopper-6.6.0-Linux-demo.pkg.tar.xz \
    -o "$archive.partial"
  mv "$archive.partial" "$archive"
fi
.tools/node/bin/node scripts/verify-hopper.mjs arch
if ! test -d .tools/hopper; then
  mkdir .tools/hopper
  tar -xJf "$archive" -C .tools/hopper opt/hopper
fi
printf '%s  %s\n' b2271008fb82bf14cfae5c3644cdde2b11fc6804bd7c99d67032ec1b1942d53c \
  .tools/hopper/opt/hopper/bin/Hopper | sha256sum --check
xvfb=.tools/downloads/xorg-x11-server-Xvfb-21.1.24-1.fc44.x86_64.rpm
if ! printf '%s  %s\n' 32ec1cc4d345055fe7aed63e3404cfef26bc219f89006a39acf24225b7c1f998 "$xvfb" | sha256sum --check --status; then
  curl -fL --connect-timeout 15 --max-time 120 \
    https://dl.fedoraproject.org/pub/fedora/linux/updates/44/Everything/x86_64/Packages/x/xorg-x11-server-Xvfb-21.1.24-1.fc44.x86_64.rpm \
    -o "$xvfb.partial"
  printf '%s  %s\n' 32ec1cc4d345055fe7aed63e3404cfef26bc219f89006a39acf24225b7c1f998 "$xvfb.partial" | sha256sum --check
  mv "$xvfb.partial" "$xvfb"
fi
host rpmkeys --checksig --verbose "$PWD/$xvfb"
if ! test -d .tools/xvfb; then
  mkdir .tools/xvfb
  host rpm2cpio "$PWD/$xvfb" > .tools/xvfb.cpio
  (cd .tools/xvfb && cpio -idmu --quiet < ../xvfb.cpio)
  rm .tools/xvfb.cpio
fi
.venv/bin/python scripts/patch-rea-xvfb.py
host "$PWD/.tools/node/bin/node" "$PWD/scripts/cache-hopper.mjs"
echo 'Hopper demo installed for scripts/rea.sh. Native smoke verification is still required.'
