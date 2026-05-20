@echo off
setlocal

REM Direct double-click launcher for FEGBA Randomizer.
REM Keeps the working directory anchored to this repository folder.
cd /d "%~dp0"

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_CMD=py -3"
) else (
    where python >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        set "PYTHON_CMD=python"
    ) else (
        echo Python 3 was not found.
        echo Please install Python 3.11 or newer from https://www.python.org/downloads/
        echo Make sure to check "Add python.exe to PATH" during install.
        echo.
        pause
        exit /b 1
    )
)

echo Launching FEGBA Randomizer...
%PYTHON_CMD% launch.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo The app did not launch successfully.
    echo If this is the first run, install dependencies with:
    echo     %PYTHON_CMD% -m pip install -r requirements.txt
    echo.
    pause
    exit /b %ERRORLEVEL%
)

endlocal
