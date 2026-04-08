#!/bin/bash
# FEGBA Randomizer Launcher for Linux/Mac
# This script handles Python path issues and launches the application

echo "========================================"
echo "  FEGBA Randomizer v1.0"
echo "  Fire Emblem GBA Character Randomizer"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python is not installed"
    echo "Please install Python 3.11 or later"
    exit 1
fi

echo "Python found."
echo ""

# Check if PySide6 is installed
python3 -c "import PySide6" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing PySide6..."
    pip3 install PySide6
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to install PySide6"
        exit 1
    fi
fi

echo "PySide6 found."
echo ""

# Add current directory to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Run the application
echo "Starting application..."
echo ""
python3 src/app.py

if [ $? -ne 0 ]; then
    echo ""
    echo "Application exited with an error."
fi