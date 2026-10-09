# -*- mode: python ; coding: utf-8 -*-
# Build with:  pyinstaller --noconfirm --clean packaging/antenna_tracker.spec
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

APP_NAME = "AntennaTracker"
BUNDLE_ID = "com.antenaa.antennatracker"
VERSION = "0.1.0"

ROOT = Path(SPECPATH).parent
SRC = ROOT / "src"
WEB_DIR = SRC / "antenna_tracker" / "ui" / "web"

datas = [(str(WEB_DIR), "antenna_tracker/ui/web")]
datas += collect_data_files("pyproj")
binaries = collect_dynamic_libs("zxingcpp") + collect_dynamic_libs("numpy")

hiddenimports = (
    collect_submodules("antenna_tracker")
    + collect_submodules("serial.tools")
    + [
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebChannel",
        "PySide6.QtMultimedia",
        "PySide6.QtMultimediaWidgets",
        "platformdirs",
        "zxingcpp",
        "numpy",
    ]
)

a = Analysis(
    [str(ROOT / "packaging" / "launcher.py")],
    pathex=[str(SRC)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    console=False,
    upx=False,
    argv_emulation=False,
)

coll = COLLECT(exe, a.binaries, a.datas, upx=False, name=APP_NAME)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name=f"{APP_NAME}.app",
        bundle_identifier=BUNDLE_ID,
        version=VERSION,
        info_plist={
            "CFBundleName": "Antenna Tracker",
            "CFBundleDisplayName": "Antenna Tracker",
            "CFBundleShortVersionString": VERSION,
            "CFBundleVersion": VERSION,
            "NSCameraUsageDescription": "Antenna Tracker uses the video capture device to show and analyse the drone video feed.",
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "11.0",
        },
    )
