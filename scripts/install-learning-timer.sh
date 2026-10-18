#!/bin/sh
# Explicit local-owner installation; never starts training or calls paid services.
set -eu
cd "$(dirname "$0")/.."
root=$(pwd)
config_dir="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
mkdir -p "$config_dir"
cat > "$config_dir/nexora-learning.service" <<EOF
[Unit]
Description=NEXORA bounded public revision discovery
[Service]
Type=oneshot
ExecStart=/usr/bin/python3 $root/scripts/learning-cycle.py
WorkingDirectory=$root
CPUQuota=50%
MemoryMax=256M
TimeoutStartSec=60
EOF
cat > "$config_dir/nexora-learning.timer" <<'EOF'
[Unit]
Description=NEXORA daily source review candidates
[Timer]
OnCalendar=*-*-* 09:00:00 Asia/Karachi
Persistent=true
RandomizedDelaySec=120
[Install]
WantedBy=timers.target
EOF
if command -v flatpak-spawn >/dev/null 2>&1; then
  flatpak-spawn --host /usr/bin/systemctl --user link "$config_dir/nexora-learning.service" "$config_dir/nexora-learning.timer"
  flatpak-spawn --host /usr/bin/systemctl --user daemon-reload
  flatpak-spawn --host /usr/bin/systemctl --user enable --now nexora-learning.timer
else
  systemctl --user daemon-reload
  systemctl --user enable --now nexora-learning.timer
fi
