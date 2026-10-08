# Changelog

## 1.0.1 - 2026-10-08

- Exclusively grab the physical multitouch event interface while Gaming Mode is active.
- Prevent Gamescope and the virtual mouse from processing the same motion in parallel.
- Reduce the tested default pointer sensitivity from `0.75` to `0.55`.
- Eliminate stationary-pointer jitter caused by duplicate physical and virtual input processing.

## 1.0.0 - 2026-10-05

- Added one-finger pointer movement and left click.
- Added two-finger scrolling and right click.
- Added three-finger middle click.
- Added hold-to-drag.
- Added automatic HTIX5288 multitouch interface detection.
- Added protection against cursor jumps during finger-count transitions.
- Added a user systemd service limited to Gaming Mode.
- Added installer, uninstaller, diagnostics, and documentation.
