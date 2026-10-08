"""Build helper: PyInstaller app, then the platform installer.

Usage: python scripts/build.py [--skip-installer]
"""

import argparse
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(*cmd: str) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, cwd=ROOT)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-installer", action="store_true")
    args = parser.parse_args()

    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    run(sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
        "--distpath", "dist", "--workpath", "build", "packaging/antenna_tracker.spec")
    if args.skip_installer:
        return 0

    if sys.platform == "darwin":
        run("bash", "installer/macos/build_dmg.sh", version)
    elif sys.platform == "win32":
        iscc = shutil.which("iscc") or r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
        run(iscc, f"/DAppVersion={version}", r"installer\windows\setup.iss")
    else:
        print("No installer for this platform; app is in dist/AntennaTracker")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
