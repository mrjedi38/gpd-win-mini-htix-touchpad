#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
install_dir="$HOME/.local/lib/gpd-htix-touchpad"
unit_dir="$HOME/.config/systemd/user"
unit_file="$unit_dir/htix-touchpad.service"

python_bin=$(command -v python3 || command -v python || true)
if [[ -z "$python_bin" ]]; then
    echo "Python 3 was not found." >&2
    exit 1
fi

if ! "$python_bin" -c 'import evdev' 2>/dev/null; then
    echo "python-evdev is missing. Install your distribution's python-evdev package first." >&2
    exit 1
fi

if [[ ! -e /dev/uinput ]]; then
    echo "/dev/uinput does not exist. Load the uinput kernel module before installing." >&2
    exit 1
fi

if ! id -nG | tr ' ' '\n' | grep -qx input; then
    echo "Warning: the current user is not a member of the input group." >&2
    echo "The service may not be able to read the physical touchpad." >&2
fi

install -d -m 0755 "$install_dir" "$unit_dir"
install -m 0755 "$project_dir/src/htix-touchpad.py" "$install_dir/htix-touchpad.py"

escaped_python=${python_bin//|/\\|}
escaped_script=${install_dir//|/\\|}/htix-touchpad.py
sed \
    -e "s|@PYTHON@|$escaped_python|g" \
    -e "s|@SCRIPT@|$escaped_script|g" \
    "$project_dir/systemd/htix-touchpad.service.in" > "$unit_file"
chmod 0644 "$unit_file"

systemctl --user daemon-reload
systemctl --user enable htix-touchpad.service

if systemctl --user is-active --quiet gamescope-session.target; then
    systemctl --user restart htix-touchpad.service
    echo "Installed and started for the active Gaming Mode session."
else
    systemctl --user stop htix-touchpad.service 2>/dev/null || true
    echo "Installed. The service will start with the next Gaming Mode session."
fi
