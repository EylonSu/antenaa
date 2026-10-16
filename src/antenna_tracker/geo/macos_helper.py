"""Read this Mac's location when the Python process has no location usage string.

Qt's permission plugin refuses to start unless the host Info.plist declares why
it needs location. A source checkout of Python does not. A small helper with
that declaration compiled into the binary can show the system prompt instead.
The packaged app has the declaration itself and does not use this helper.
"""

from __future__ import annotations

import math
import shutil
import subprocess
import threading
from importlib.resources import files
from pathlib import Path

from platformdirs import user_cache_dir
from PySide6.QtCore import QThread, Signal

from antenna_tracker.config import APP_NAME

_HELPER_NAMES = ("macos_location_helper.swift", "macos_location_helper.plist")


def parse_helper_output(text: str) -> tuple[float, float, float] | None:
    """Latitude, longitude, and altitude in metres. Altitude is NaN when unknown."""
    parts = text.split()
    if len(parts) < 2:
        return None
    try:
        lat = float(parts[0])
        lon = float(parts[1])
        alt = float(parts[2]) if len(parts) > 2 else math.nan
    except ValueError:
        return None
    if not math.isfinite(lat) or not math.isfinite(lon):
        return None
    if not -90.0 <= lat <= 90.0 or not -180.0 <= lon <= 180.0:
        return None
    if not math.isfinite(alt) or not -500.0 <= alt <= 4000.0:
        alt = math.nan
    return lat, lon, alt


def _resource_text(name: str) -> str:
    return files("antenna_tracker.geo").joinpath(name).read_text(encoding="utf-8")


def ensure_location_helper() -> Path:
    """Return a cached helper app, compiling it with swiftc when needed.

    A bare executable never receives the macOS location panel. The binary has to
    live in an app bundle whose Info.plist states why it needs location.
    """
    cache = Path(user_cache_dir(APP_NAME, appauthor=False)) / "location-helper"
    app = cache / "antenaa-location.app"
    binary = app / "Contents" / "MacOS" / "antenaa-location"
    plist_path = app / "Contents" / "Info.plist"
    swift = _resource_text(_HELPER_NAMES[0])
    plist = _resource_text(_HELPER_NAMES[1])
    payload = swift + "\n---\n" + plist
    stamp = cache / "source.stamp"
    if binary.is_file() and plist_path.is_file() and stamp.is_file() and stamp.read_text(encoding="utf-8") == payload:
        return app
    compiler = shutil.which("swiftc")
    if compiler is None:
        raise FileNotFoundError("swiftc")
    binary.parent.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    swift_path = cache / "location-helper.swift"
    swift_path.write_text(swift, encoding="utf-8")
    plist_path.write_text(plist, encoding="utf-8")
    compiled = subprocess.run(
        [compiler, "-o", str(binary), str(swift_path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if compiled.returncode != 0:
        detail = (compiled.stderr or compiled.stdout or "swiftc failed").strip()
        raise RuntimeError(detail)
    codesign = shutil.which("codesign")
    if codesign is not None:
        subprocess.run(
            [codesign, "--force", "--deep", "--sign", "-", str(app)],
            check=False,
            capture_output=True,
        )
    xattr = shutil.which("xattr")
    if xattr is not None:
        subprocess.run([xattr, "-dr", "com.apple.quarantine", str(app)], check=False, capture_output=True)
    stamp.write_text(payload, encoding="utf-8")
    return app


class MacosLocationThread(QThread):
    """Compile (once) and run the helper off the UI thread."""

    found = Signal(float, float, float)
    unavailable = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._lock = threading.Lock()
        self._proc: subprocess.Popen[str] | None = None
        self.failure = ""

    def run(self) -> None:
        try:
            app = ensure_location_helper()
        except (OSError, RuntimeError, ValueError):
            self._fail()
            return
        if self.isInterruptionRequested():
            return
        binary = app / "Contents" / "MacOS" / "antenaa-location"
        output = app.parent / "last-fix.txt"
        output.unlink(missing_ok=True)
        proc = subprocess.Popen(
            [str(binary), str(output)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        with self._lock:
            self._proc = proc
        try:
            proc.wait(timeout=200)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            self._fail("timeout")
            return
        finally:
            with self._lock:
                self._proc = None
        if self.isInterruptionRequested():
            return
        line = ""
        try:
            line = output.read_text(encoding="utf-8").strip().splitlines()[0]
        except (OSError, IndexError):
            line = ""
        if line == "denied":
            self._fail("denied")
            return
        fix = parse_helper_output(line)
        if fix is None:
            self._fail("timeout" if line == "timeout" else "")
            return
        self.found.emit(*fix)

    def stop(self) -> None:
        self.requestInterruption()
        with self._lock:
            proc = self._proc
        if proc is not None and proc.poll() is None:
            proc.kill()

    def _fail(self, reason: str = "") -> None:
        self.failure = reason
        if not self.isInterruptionRequested():
            self.unavailable.emit()
