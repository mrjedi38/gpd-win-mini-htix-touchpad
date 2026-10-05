#!/usr/bin/env bash
set -euo pipefail

unit_file="$HOME/.config/systemd/user/htix-touchpad.service"
install_dir="$HOME/.local/lib/gpd-htix-touchpad"

systemctl --user disable --now htix-touchpad.service 2>/dev/null || true
rm -f "$unit_file"
rm -rf "$install_dir"
systemctl --user daemon-reload
systemctl --user reset-failed

echo "Removed the HTIX5288 Gaming Mode touchpad bridge."
