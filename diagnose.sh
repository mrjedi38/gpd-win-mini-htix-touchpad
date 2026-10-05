#!/usr/bin/env bash
set -u

printf '%s\n' '=== system ==='
uname -a

printf '%s\n' '' '=== session targets ==='
systemctl --user show gamescope-session.target -p ActiveState -p SubState 2>&1 || true
systemctl --user show htix-touchpad.service -p ActiveState -p SubState -p MainPID -p Result 2>&1 || true

printf '%s\n' '' '=== matching input devices ==='
python3 - <<'PY'
from pathlib import Path
text = Path('/proc/bus/input/devices').read_text(errors='replace')
blocks = [block for block in text.split('\n\n') if 'HTIX5288' in block or 'Virtual Mouse' in block]
print('\n\n'.join(blocks) if blocks else 'No matching devices found.')
PY

printf '%s\n' '' '=== recent service log ==='
journalctl --user -u htix-touchpad.service -n 30 --no-pager 2>&1 || true

printf '%s\n' '' '=== permissions ==='
stat -c '%A %U:%G %n' /dev/uinput /dev/input/event* 2>/dev/null || true
