#!/usr/bin/env python3
"""
Direct launcher for FEGBA Randomizer.

Run with:
    python launch.py

This wrapper keeps users from needing to know the internal entry point
(``src/app.py``). It also prints a friendly dependency hint if PySide6 or
Pillow is not installed yet, and offers to install them automatically.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
REQUIREMENTS = ROOT_DIR / "requirements.txt"


def _ensure_root_on_path() -> None:
    """Make sure ``import src.*`` resolves no matter where we were launched from."""
    root = str(ROOT_DIR)
    if root not in sys.path:
        sys.path.insert(0, root)


def _python_version_check() -> None:
    if sys.version_info < (3, 9):
        print("FEGBA Randomizer requires Python 3.9 or newer.")
        print(f"You are running Python {sys.version.split()[0]}.")
        print("Please install Python 3.11+ from https://www.python.org/downloads/")
        raise SystemExit(1)


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

    install_cmd: list[str]
    if REQUIREMENTS.exists():
        print("Install them with:")
        print(f"    {sys.executable} -m pip install -r requirements.txt")
        install_cmd = [
            sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS),
        ]
    else:
        print("Install them with:")
        print(f"    {sys.executable} -m pip install PySide6 Pillow")
        install_cmd = [
            sys.executable, "-m", "pip", "install", "PySide6", "Pillow",
        ]
    print()

    # In an interactive console, offer to install automatically.
    if sys.stdin and sys.stdin.isatty():
        try:
            answer = input("Install dependencies now? [Y/n]: ").strip().lower()
        except EOFError:
            answer = "n"
        if answer in ("", "y", "yes"):
            try:
                subprocess.check_call(install_cmd)
                return
            except subprocess.CalledProcessError as exc:
                print(f"\nInstall failed (exit code {exc.returncode}).")
                raise SystemExit(exc.returncode)

    raise SystemExit(1)


def main() -> None:
    _python_version_check()
    os.chdir(ROOT_DIR)
    _ensure_root_on_path()
    _dependency_check()

    # Import lazily so that the dependency check above runs first
    # and we can give a clean error message before Python tries to
    # resolve the PySide6 imports inside ``src.app``.
    from src.app import main as app_main

    app_main()


if __name__ == "__main__":
    main()
