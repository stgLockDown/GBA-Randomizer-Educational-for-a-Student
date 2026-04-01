"""
Logs Tab: spoiler log viewer and export.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QFileDialog, QGroupBox, QApplication
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class LogsTab(QWidget):
    def __init__(self, app_state, parent=None):
        super().__init__(parent)
        self.state = app_state
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Header
        header_layout = QHBoxLayout()
        header_label = QLabel("📜 Spoiler Log")
        header_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #90caf9;")
        header_layout.addWidget(header_label)
        header_layout.addStretch()

        self.copy_log_btn = QPushButton("📋 Copy Log")
        self.copy_log_btn.clicked.connect(self._copy_log)
        header_layout.addWidget(self.copy_log_btn)

        self.save_log_btn = QPushButton("💾 Save As...")
        self.save_log_btn.clicked.connect(self._save_log)
        header_layout.addWidget(self.save_log_btn)

        layout.addLayout(header_layout)

        # Info bar
        self.info_label = QLabel("Build a ROM to generate a spoiler log.")
        self.info_label.setStyleSheet("color: #78909c; font-size: 11px; padding: 4px;")
        layout.addWidget(self.info_label)

        # Log viewer
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        # Set monospace font with safeguards
        try:
            mono_font = QFont("Consolas", 10) if QFont("Consolas", 10).exactMatch() else QFont("Courier New", 10)
            if mono_font.pointSize() is None or mono_font.pointSize() <= 0:
                mono_font.setPointSize(10)
            self.log_view.setFont(mono_font)
        except Exception:
            pass  # Use default font if there's an issue
        self.log_view.setStyleSheet("""
            QTextEdit {
                background: #0a0a14;
                border: 1px solid #303050;
                border-radius: 4px;
                padding: 8px;
                color: #b0bec5;
                line-height: 1.4;
            }
        """)
        self.log_view.setPlaceholderText(
            "Spoiler log will appear here after a successful build.\n\n"
            "The log includes:\n"
            "  • Seed and settings hash\n"
            "  • ROM and profile identification\n"
            "  • Before/after data for every character\n"
            "  • Validation warnings and auto-fixes\n\n"
            "You can also find the log files in the output folder:\n"
            "  • spoiler_{seed}.txt\n"
            "  • spoiler_{seed}.json"
        )
        layout.addWidget(self.log_view, 1)

        # File locations
        files_group = QGroupBox("Output File Locations")
        files_layout = QVBoxLayout(files_group)

        self.txt_path_label = QLabel("Text log: —")
        self.txt_path_label.setStyleSheet("color: #78909c; font-size: 11px;")
        self.txt_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        files_layout.addWidget(self.txt_path_label)

        self.json_path_label = QLabel("JSON log: —")
        self.json_path_label.setStyleSheet("color: #78909c; font-size: 11px;")
        self.json_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        files_layout.addWidget(self.json_path_label)

        self.rom_path_label = QLabel("Output ROM/Patch: —")
        self.rom_path_label.setStyleSheet("color: #78909c; font-size: 11px;")
        self.rom_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        files_layout.addWidget(self.rom_path_label)

        layout.addWidget(files_group)

    def refresh(self):
        """Refresh the log display from app state."""
        content = self.state.last_spoiler_content
        if content:
            self.log_view.setPlainText(content)
            self.info_label.setText(f"✅ Spoiler log generated for seed: {self.state.settings.seed}")
            self.info_label.setStyleSheet("color: #66bb6a; font-size: 11px; padding: 4px;")
        else:
            self.log_view.clear()
            self.info_label.setText("No spoiler log available.")
            self.info_label.setStyleSheet("color: #78909c; font-size: 11px; padding: 4px;")

        # Update file locations
        if self.state.last_spoiler_txt:
            self.txt_path_label.setText(f"Text log: {self.state.last_spoiler_txt}")
        if self.state.last_spoiler_json:
            self.json_path_label.setText(f"JSON log: {self.state.last_spoiler_json}")
        if self.state.last_output_path:
            self.rom_path_label.setText(f"Output: {self.state.last_output_path}")

    def _copy_log(self):
        text = self.log_view.toPlainText()
        if text:
            QApplication.clipboard().setText(text)

    def _save_log(self):
        text = self.log_view.toPlainText()
        if not text:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Spoiler Log", "",
            "Text Files (*.txt);;All Files (*)"
        )
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text)