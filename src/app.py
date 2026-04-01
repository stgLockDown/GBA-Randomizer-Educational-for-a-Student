"""FEGBA Randomizer — Main Application Entry Point
Fire Emblem GBA Character Randomizer (FE6/FE7/FE8 + Skill System)
"""
import sys
import os

# Get the directory containing this script (src/app.py)
script_dir = os.path.dirname(os.path.abspath(__file__))

# Get the parent directory (repository root)
parent_dir = os.path.dirname(script_dir)

# Ensure script_dir (src) is in sys.path
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Ensure parent_dir is also in sys.path
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

# Import using relative imports from src directory
from ui.models.app_state import AppState
from ui.main_window import MainWindow


def main():
    # High DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # Disable context help button (Windows fix) - use safe attribute access
    try:
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_DisableWindowContextHelpButton, True)
    except AttributeError:
        pass  # Attribute not available in this PySide6 version

    app = QApplication(sys.argv)
    app.setApplicationName("FEGBA Randomizer")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("FEGBA")

    # Set default font (with safeguards for invalid point sizes)
    try:
        font = QFont("Segoe UI", 10)
        if not font.exactMatch():
            font = QFont("sans-serif", 10)
        # Ensure point size is valid (Qt can crash with invalid sizes)
        if font.pointSize() is None or font.pointSize() <= 0:
            font.setPointSize(10)
        app.setFont(font)
    except Exception as e:
        print(f"Warning: Could not set default font: {e}")
        # Fall back to system default
        pass

    # Create app state (loads profiles, layouts, presets)
    state = AppState()

    # Create and show main window
    window = MainWindow(state)
    window.show()
    
    # Force window to render (Windows black screen fix)
    window.raise_()
    window.activateWindow()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()