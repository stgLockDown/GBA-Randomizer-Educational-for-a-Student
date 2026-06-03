#!/usr/bin/env bash
# Direct launcher for FEGBA Randomizer (Linux / macOS).
# Keeps the working directory anchored to this script's folder.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD=python3
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD=python
else
    echo "Python 3 was not found."
    echo "Please install Python 3.11 or newer from https://www.python.org/downloads/"
    exit 1
fi

echo "Launching FEGBA Randomizer..."
exec "$PYTHON_CMD" launch.py "$@"
