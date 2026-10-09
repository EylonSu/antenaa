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
UI_ASSETS = SRC / "antenna_tracker" / "ui" / "assets"

datas = [(str(WEB_DIR), "antenna_tracker/ui/web"),
         (str(UI_ASSETS), "antenna_tracker/ui/assets"),
         (str(ROOT / "packaging" / "icons" / "icon.png"), "antenna_tracker/assets")]
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
    icon=str(ROOT / "packaging" / "icons" / "icon.ico"),
)

coll = COLLECT(exe, a.binaries, a.datas, upx=False, name=APP_NAME)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name=f"{APP_NAME}.app",
        bundle_identifier=BUNDLE_ID,
        version=VERSION,
        icon=str(ROOT / "packaging" / "icons" / "icon.icns"),
        info_plist={
            "CFBundleName": "antenaa",
            "CFBundleDisplayName": "antenaa",
            "CFBundleShortVersionString": VERSION,
            "CFBundleVersion": VERSION,
            "NSCameraUsageDescription": "antenaa uses the video capture device to show and analyse the drone video feed.",
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "11.0",
        },
    )
