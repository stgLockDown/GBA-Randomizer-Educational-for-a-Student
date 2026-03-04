"""
FEGBA Randomizer — Main Application Entry Point
Fire Emblem GBA Character Randomizer (FE6/FE7/FE8 + Skill System)
"""
import sys
import os

# Ensure src package is importable
src_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(src_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from src.ui.models.app_state import AppState
from src.ui.main_window import MainWindow


def main():
    # High DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("FEGBA Randomizer")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("FEGBA")

    # Set default font
    font = QFont("Segoe UI", 10)
    if not font.exactMatch():
        font = QFont("sans-serif", 10)
    app.setFont(font)

    # Create app state (loads profiles, layouts, presets)
    state = AppState()

    # Create and show main window
    window = MainWindow(state)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()