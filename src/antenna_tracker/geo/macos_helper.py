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
    """Return a cached helper binary, compiling it with swiftc when needed."""
    cache = Path(user_cache_dir(APP_NAME, appauthor=False)) / "location-helper"
    cache.mkdir(parents=True, exist_ok=True)
    binary = cache / "antenaa-location"
    swift = _resource_text(_HELPER_NAMES[0])
    plist = _resource_text(_HELPER_NAMES[1])
    payload = swift + "\n---\n" + plist
    stamp = cache / "source.stamp"
    if binary.is_file() and stamp.is_file() and stamp.read_text(encoding="utf-8") == payload:
        return binary
    compiler = shutil.which("swiftc")
    if compiler is None:
        raise FileNotFoundError("swiftc")
    swift_path = cache / "location-helper.swift"
    plist_path = cache / "location-helper.plist"
    swift_path.write_text(swift, encoding="utf-8")
    plist_path.write_text(plist, encoding="utf-8")
    compiled = subprocess.run(
        [
            compiler,
            "-o",
            str(binary),
            str(swift_path),
            "-Xlinker",
            "-sectcreate",
            "-Xlinker",
            "__TEXT",
            "-Xlinker",
            "__info_plist",
            "-Xlinker",
            str(plist_path),
        ],
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
            [codesign, "--force", "--sign", "-", str(binary)],
            check=False,
            capture_output=True,
        )
    stamp.write_text(payload, encoding="utf-8")
    return binary


class MacosLocationThread(QThread):
    """Compile (once) and run the helper off the UI thread."""

    found = Signal(float, float, float)
    unavailable = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._lock = threading.Lock()
        self._proc: subprocess.Popen[str] | None = None

    def run(self) -> None:
        try:
            binary = ensure_location_helper()
        except (OSError, RuntimeError, ValueError):
            self._fail()
            return
        if self.isInterruptionRequested():
            return
        proc = subprocess.Popen(
            [str(binary)],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        with self._lock:
            self._proc = proc
        try:
            out, _ = proc.communicate(timeout=200)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            self._fail()
            return
        finally:
            with self._lock:
                self._proc = None
        if self.isInterruptionRequested() or proc.returncode != 0:
            self._fail()
            return
        fix = parse_helper_output(out)
        if fix is None:
            self._fail()
            return
        self.found.emit(*fix)

    def stop(self) -> None:
        self.requestInterruption()
        with self._lock:
            proc = self._proc
        if proc is not None and proc.poll() is None:
            proc.kill()

    def _fail(self) -> None:
        if not self.isInterruptionRequested():
            self.unavailable.emit()
