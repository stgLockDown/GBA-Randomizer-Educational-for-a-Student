#!/usr/bin/env python3
"""
Build script for FEGBA Randomizer.
Uses Nuitka to produce a standalone Windows executable.
Run on Windows: python build.py
"""
import os
import subprocess
import shutil
import sys

APP_NAME = "FEGBA_Randomizer"
MAIN_SCRIPT = "src/app.py"
ICON_PATH = "src/assets/icons/app_icon.ico"
OUTPUT_DIR = "dist"
ZIP_NAME = f"{APP_NAME}_portable"

NUITKA_CMD = [
    sys.executable, "-m", "nuitka",
    "--standalone",
    "--onefile",
    f"--output-filename={APP_NAME}.exe",
    f"--output-dir={OUTPUT_DIR}",
    "--enable-plugin=pyside6",
    "--include-data-dir=src/assets=assets",
    "--include-data-dir=src/profiles=profiles",
    "--include-data-dir=src/presets=presets",
    "--include-data-dir=src/layouts=layouts",
    "--windows-console-mode=disable",
    f"--windows-icon-from-ico={ICON_PATH}",
    "--company-name=FEGBA Randomizer",
    f"--product-name={APP_NAME}",
    "--product-version=1.0.0",
    "--file-description=Fire Emblem GBA Character Randomizer",
    MAIN_SCRIPT,
]


def build():
    print(f"[*] Building {APP_NAME} with Nuitka...")
    print(f"    Command: {' '.join(NUITKA_CMD)}")
    result = subprocess.run(NUITKA_CMD)
    if result.returncode != 0:
        print("[!] Nuitka build failed.")
        sys.exit(1)
    print("[+] Build succeeded.")


def package_zip():
    """Create a portable ZIP of the dist folder."""
    print(f"[*] Packaging {ZIP_NAME}.zip ...")
    if os.path.exists(f"{OUTPUT_DIR}/{ZIP_NAME}.zip"):
        os.remove(f"{OUTPUT_DIR}/{ZIP_NAME}.zip")
    shutil.make_archive(
        os.path.join(OUTPUT_DIR, ZIP_NAME),
        'zip',
        root_dir=OUTPUT_DIR,
    )
    print(f"[+] Created {OUTPUT_DIR}/{ZIP_NAME}.zip")


if __name__ == "__main__":
    build()
    package_zip()
    print("[+] Done. Distribute the ZIP file.")