#!/usr/bin/env python3
"""
Direct launcher for FEGBA Randomizer.

Run with:
    python launch.py

This wrapper keeps users from needing to know the internal entry point
(`src/app.py`). It also prints a friendly dependency hint if PySide6 or
Pillow is not installed yet.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
REQUIREMENTS = ROOT_DIR / "requirements.txt"


def _ensure_root_on_path() -> None:
    root = str(ROOT_DIR)
    if root not in sys.path:
        sys.path.insert(0, root)


def _dependency_check() -> None:
    missing: list[str] = []
    try:
        import PySide6  # noqa: F401
    except ImportError:
        missing.append("PySide6")

    try:
        import PIL  # noqa: F401
    except ImportError:
        missing.append("Pillow")

    if not missing:
        return

    print("Missing required Python packages: " + ", ".join(missing))
    print()
    if REQUIREMENTS.exists():
        print("Install them with:")
        print(f"    {sys.executable} -m pip install -r requirements.txt")
        print()

        # In an interactive console, offer to install automatically.
        if sys.stdin.isatty():
            answer = input("Install dependencies now? [Y/n]: ").strip().lower()
            if answer in ("", "y", "yes"):
                subprocess.check_call([
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "-r",
                    str(REQUIREMENTS),
                ])
                return
    else:
        print("Install them with:")
        print(f"    {sys.executable} -m pip install PySide6 Pillow")
        print()

    raise SystemExit(1)


def main() -> None:
    os.chdir(ROOT_DIR)
    _ensure_root_on_path()
    _dependency_check()

    from src.app import main as app_main

    app_main()


if __name__ == "__main__":
    main()
