@echo off
REM FEGBA Randomizer Launcher for Windows
REM This script handles Python path issues and launches the application

echo ========================================
echo   FEGBA Randomizer v1.0
echo   Fire Emblem GBA Character Randomizer
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.11 or later from https://www.python.org/
    pause
    exit /b 1
)

echo Python found.
echo.

REM Check if PySide6 is installed
python -c "import PySide6" >nul 2>&1
if errorlevel 1 (
    echo Installing PySide6...
    pip install PySide6
    if errorlevel 1 (
        echo ERROR: Failed to install PySide6
        pause
        exit /b 1
    )
)

echo PySide6 found.
echo.

REM Add current directory to Python path
set PYTHONPATH=%PYTHONPATH%;%CD%

REM Run the application
echo Starting application...
echo.
python src\app.py

if errorlevel 1 (
    echo.
    echo Application exited with an error.
    pause
)