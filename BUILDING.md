# Building Antenna Tracker

Requires Python 3.12.

```bash
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e . pyinstaller
python scripts/build.py                          # app + installer for the current OS
python scripts/build.py --skip-installer         # only dist/AntennaTracker(.app)
```

## macOS

Produces `dist/AntennaTracker.app` and `dist/AntennaTracker-<version>.dmg`.
`brew install create-dmg` gives a nicer DMG; without it `hdiutil` is used.
The bundle includes `NSCameraUsageDescription` so the camera prompt appears.
The app is unsigned; on first launch right-click > Open (notarization needs an Apple Developer account).

## Windows

PyInstaller cannot cross-compile, so build on Windows or in CI.

1. `pwsh installer/windows/drivers/fetch_drivers.ps1` (downloads CH340 + FTDI drivers, see `installer/windows/drivers/README.md`).
2. Install [Inno Setup 6](https://jrsoftware.org/isinfo.php).
3. `python scripts/build.py` → `dist/AntennaTracker-<version>-setup.exe`.

The installer needs admin rights; it creates Start menu/desktop shortcuts and silently installs the drivers with `pnputil`.

## CI

`.github/workflows/build.yml` builds both platforms on every push/PR and uploads the `setup.exe` and `.dmg` as artifacts.
