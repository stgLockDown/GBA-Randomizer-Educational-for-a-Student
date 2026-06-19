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

    # After window is shown, check if loaded profile has translation warnings
    def _check_translation_warning(success, message):
        if success and state.profile:
            translation_meta = state.profile.get('translation_metadata', {})
            if translation_meta.get('is_translation_patch', False):
                warnings = state.profile.get('warnings', [])
                if warnings:
                    from PySide6.QtWidgets import QMessageBox
                    warning_text = "\n".join(f"• {w}" for w in warnings)
                    QMessageBox.warning(
                        window,
                        "Translation-Patched ROM Detected",
                        f"This ROM uses a translation patch with known limitations:\n\n"
                        f"{warning_text}\n\n"
                        f"Some randomization features have been automatically disabled for safety.",
                    )

    state.rom_loaded.connect(_check_translation_warning)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
