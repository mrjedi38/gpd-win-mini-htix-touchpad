# GPD Win Mini HTIX5288 touchpad bridge

A small userspace driver for the HTIX5288 touchpad found in the GPD Win Mini 2025. It converts multitouch events into a virtual mouse that Steam Gaming Mode and Gamescope can use reliably.

The service runs only while `gamescope-session.target` is active. KDE/Desktop Mode keeps the original touchpad and its normal libinput behavior.

## Why this exists

On the tested GPD Win Mini 2025, the HTIX5288 works as a normal touchpad in KDE, but Gaming Mode does not reliably produce mouse clicks from it. Movement may work while tap-to-click does not.

This project reads the multitouch event interface and creates `HTIX5288 Virtual Mouse` through Linux uinput.

```text
HTIX5288 multitouch events
            |
            v
     htix-touchpad.py
            |
            v
        /dev/uinput
            |
            v
 HTIX5288 Virtual Mouse
            |
            v
 Steam / Gamescope Gaming Mode
```

## Features

- one-finger pointer movement
- one-finger tap for left click
- two-finger tap for right click
- three-finger tap for middle click
- vertical and horizontal two-finger scrolling
- hold-to-drag with one finger
- right-button hold with two fingers
- protection against cursor jumps after finger-count changes
- automatic event-device discovery; no hardcoded `/dev/input/eventX`
- automatic start and stop with Gaming Mode

## Tested setup

- GPD Win Mini 2025
- HTIX5288, USB/I2C ID `0911:5288`
- CachyOS Handheld/Deckify
- Linux 7.2 series
- Steam Gaming Mode using `gamescope-session.target`

Other distributions and HTIX5288 devices may work, but have not been tested yet.

## Requirements

- Python 3
- [`python-evdev`](https://python-evdev.readthedocs.io/)
- `/dev/uinput`
- permission to read `/dev/input/event*` and write `/dev/uinput`
- a user systemd session with `gamescope-session.target`

Check the Python dependency:

```bash
python3 -c "import evdev; print('python-evdev: OK')"
```

Check your groups:

```bash
id -nG
```

On many distributions, the account needs membership in the `input` group. Group changes require a new login session.

## Installation

```bash
git clone https://github.com/mrjedi38/gpd-win-mini-htix-touchpad.git
cd gpd-win-mini-htix-touchpad
./install.sh
```

The installer copies the script to:

```text
~/.local/lib/gpd-htix-touchpad/htix-touchpad.py
```

and installs this user service:

```text
~/.config/systemd/user/htix-touchpad.service
```

If Gaming Mode is already active, the installer starts the service immediately. Otherwise it starts on the next Gaming Mode session.

## Verification

In Gaming Mode:

```bash
systemctl --user status htix-touchpad.service
```

The log should contain a line similar to:

```text
Running on /dev/input/event11: HTIX5288:00 0911:5288
```

Find the virtual device:

```bash
grep -A6 -B2 "HTIX5288 Virtual Mouse" /proc/bus/input/devices
```

In Desktop Mode, the service should be inactive:

```bash
systemctl --user is-active htix-touchpad.service
```

Expected result:

```text
inactive
```

## Controls

| Gesture | Mouse action |
|---|---|
| Move one finger | Move pointer |
| Tap one finger | Left click |
| Hold one finger | Hold left button / drag |
| Tap two fingers | Right click |
| Hold two fingers | Hold right button |
| Move two fingers vertically | Vertical scroll |
| Move two fingers horizontally | Horizontal scroll |
| Tap three fingers | Middle click |

## Tuning

The main settings are near the top of `src/htix-touchpad.py`:

```python
SENSITIVITY = 0.75
DEADZONE = 2
SMOOTH = 4
MAX_POINTER_DELTA = 180
TAP_TIME = 0.22
HOLD_TIME = 0.90
```

`MAX_POINTER_DELTA` rejects implausible single-frame jumps. If fast intentional movement gets clipped, increase it gradually.

After editing the installed copy, restart the service:

```bash
systemctl --user restart htix-touchpad.service
```

## How device detection works

The event number is not stable. The same touchpad has appeared as both `/dev/input/event9` and `/dev/input/event11`, and its name may or may not include the word `Touchpad`.

The script therefore:

1. scans `/dev/input/event*`;
2. matches the stable prefix `HTIX5288:00 0911:5288`;
3. selects the interface exposing `ABS_MT_SLOT`, `ABS_MT_POSITION_X`, `ABS_MT_POSITION_Y`, and `ABS_MT_TRACKING_ID`.

This also avoids selecting the sibling relative-mouse interface exposed by the same hardware.

## Uninstallation

```bash
./uninstall.sh
```

The uninstaller stops the service, removes the installed files, and reloads the user systemd manager. The physical touchpad is not modified.

## Troubleshooting

Run:

```bash
./diagnose.sh
```

Common problems:

- `HTIX5288 multitouch event device not found`: verify that the kernel created the HTIX5288 input interfaces.
- `Permission denied`: verify access to `/dev/input/event*` and `/dev/uinput`.
- Service remains inactive in Gaming Mode: verify that your distribution uses `gamescope-session.target`.
- Duplicate or unusually fast pointer movement: another HTIX interface may also be consumed by Gamescope. Include `libinput list-devices`, `/proc/bus/input/devices`, and the service log in a bug report.

Do not add a global `LIBINPUT_IGNORE_DEVICE=1` rule for the physical HTIX5288 if you want the original touchpad to work in Desktop Mode.

## Polski skrót

Mod naprawia obsługę kliknięć touchpada HTIX5288 w Gaming Mode na GPD Win Mini 2025. Wirtualna mysz działa tylko podczas sesji Gamescope. Po przejściu do KDE usługa zatrzymuje się i system ponownie korzysta z oryginalnego touchpada.

## License

MIT. See [LICENSE](LICENSE).
