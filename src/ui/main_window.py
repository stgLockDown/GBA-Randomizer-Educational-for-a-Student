"""
Main Window: primary application window with left Build panel and right tab area.
"""
import os
import sys
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QLabel, QPushButton, QLineEdit, QComboBox, QRadioButton,
    QButtonGroup, QGroupBox, QFileDialog, QMessageBox, QTabWidget,
    QProgressBar, QApplication, QFrame, QToolButton, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QSize, QMimeData
from PySide6.QtGui import QFont, QIcon, QDragEnterEvent, QDropEvent, QPixmap, QColor, QPalette

from src.ui.tabs.characters_tab import CharactersTab
from src.ui.tabs.classes_tab import ClassesTab
from src.ui.tabs.stats_tab import StatsTab
from src.ui.tabs.items_tab import ItemsTab
from src.ui.tabs.safety_tab import SafetyTab
from src.ui.tabs.advanced_tab import AdvancedTab
from src.ui.tabs.preview_tab import PreviewTab
from src.ui.tabs.logs_tab import LogsTab
from src.ui.models.app_state import AppState


class ROMDropZone(QLabel):
    """Drag-and-drop zone for ROM files."""
    rom_dropped = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumHeight(60)
        self.setText("📂 Drop ROM here or click Browse...")
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #5c6bc0;
                border-radius: 8px;
                padding: 12px;
                color: #b0bec5;
                background: #1a1a2e;
                font-size: 12px;
            }
            QLabel:hover {
                border-color: #7986cb;
                background: #1e1e38;
            }
        """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith('.gba'):
                    event.acceptProposedAction()
                    self.setStyleSheet(self.styleSheet().replace("#1a1a2e", "#252550"))
                    return
        event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet(self.styleSheet().replace("#252550", "#1a1a2e"))

    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet(self.styleSheet().replace("#252550", "#1a1a2e"))
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith('.gba'):
                self.rom_dropped.emit(path)
                return


class MainWindow(QMainWindow):
    """Primary application window."""

    def __init__(self, app_state: AppState):
        super().__init__()
        self.state = app_state

        self.setWindowTitle("FEGBA Randomizer v1.0 — Fire Emblem GBA Character Randomizer")
        self.setMinimumSize(1100, 720)
        self.resize(1280, 800)

        self._apply_dark_theme()
        self._build_ui()
        self._connect_signals()

    def _apply_dark_theme(self):
        """Apply a comprehensive dark theme covering all widget types."""
        self.setStyleSheet("""
            /* ── Base ── */
            QMainWindow, QDialog {
                background: #0f0f1a;
            }
            QWidget {
                color: #e0e0e0;
                background: #0f0f1a;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 12px;
            }

            /* ── GroupBox ── */
            QGroupBox {
                border: 1px solid #303050;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 18px;
                font-weight: bold;
                color: #90caf9;
                background: #12121f;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                color: #90caf9;
            }

            /* ── Buttons ── */
            QPushButton {
                background: #283593;
                border: none;
                border-radius: 4px;
                padding: 7px 18px;
                color: #ffffff;
                font-weight: bold;
            }
            QPushButton:hover { background: #3949ab; }
            QPushButton:pressed { background: #1a237e; }
            QPushButton:disabled { background: #2a2a3a; color: #555570; }
            QPushButton#buildBtn {
                background: #2e7d32;
                font-size: 14px;
                padding: 10px 24px;
                color: #ffffff;
            }
            QPushButton#buildBtn:hover { background: #388e3c; }
            QPushButton#buildBtn:disabled { background: #1b3a1d; color: #556b55; }
            QPushButton#previewBtn { background: #00695c; color: #ffffff; }
            QPushButton#previewBtn:hover { background: #00897b; }

            /* ── Text Inputs ── */
            QLineEdit {
                background: #1a1a2e;
                border: 1px solid #303050;
                border-radius: 4px;
                padding: 5px 8px;
                color: #e0e0e0;
            }
            QLineEdit:focus { border-color: #5c6bc0; }
            QLineEdit:disabled { background: #141420; color: #555570; }

            /* ── ComboBox ── */
            QComboBox {
                background: #1a1a2e;
                border: 1px solid #303050;
                border-radius: 4px;
                padding: 5px 8px;
                color: #e0e0e0;
            }
            QComboBox:hover { border-color: #5c6bc0; }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                width: 10px;
                height: 10px;
            }
            QComboBox QAbstractItemView {
                background: #1a1a2e;
                border: 1px solid #303050;
                color: #e0e0e0;
                selection-background-color: #283593;
                selection-color: #ffffff;
                outline: none;
            }

            /* ── CheckBox ── */
            QCheckBox {
                color: #e0e0e0;
                background: transparent;
                spacing: 6px;
            }
            QCheckBox:disabled { color: #555570; }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border: 1px solid #5c6bc0;
                border-radius: 3px;
                background: #1a1a2e;
            }
            QCheckBox::indicator:checked {
                background: #5c6bc0;
                border-color: #7986cb;
            }
            QCheckBox::indicator:hover {
                border-color: #7986cb;
                background: #252545;
            }

            /* ── RadioButton ── */
            QRadioButton {
                color: #e0e0e0;
                background: transparent;
                spacing: 6px;
            }
            QRadioButton::indicator {
                width: 14px;
                height: 14px;
                border: 1px solid #5c6bc0;
                border-radius: 7px;
                background: #1a1a2e;
            }
            QRadioButton::indicator:checked {
                background: #5c6bc0;
                border-color: #7986cb;
            }

            /* ── SpinBox ── */
            QSpinBox, QDoubleSpinBox {
                background: #1a1a2e;
                border: 1px solid #303050;
                border-radius: 4px;
                padding: 4px 6px;
                color: #e0e0e0;
            }
            QSpinBox:focus, QDoubleSpinBox:focus { border-color: #5c6bc0; }
            QSpinBox::up-button, QSpinBox::down-button,
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                background: #252545;
                border: none;
                width: 16px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover,
            QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
                background: #303060;
            }

            /* ── Slider ── */
            QSlider::groove:horizontal {
                border: 1px solid #303050;
                height: 4px;
                background: #252545;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #5c6bc0;
                border: none;
                width: 14px;
                height: 14px;
                border-radius: 7px;
                margin: -5px 0;
            }
            QSlider::handle:horizontal:hover { background: #7986cb; }
            QSlider::sub-page:horizontal {
                background: #3949ab;
                border-radius: 2px;
            }

            /* ── Tabs ── */
            QTabWidget::pane {
                border: 1px solid #303050;
                border-radius: 4px;
                background: #12121f;
            }
            QTabBar::tab {
                background: #1a1a2e;
                border: 1px solid #303050;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 6px 14px;
                margin-right: 2px;
                color: #90a4ae;
            }
            QTabBar::tab:selected {
                background: #12121f;
                color: #90caf9;
                font-weight: bold;
            }
            QTabBar::tab:hover { color: #bbdefb; background: #1e1e38; }

            /* ── ScrollArea ── */
            QScrollArea {
                background: #12121f;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background: #12121f;
            }

            /* ── ScrollBars ── */
            QScrollBar:vertical {
                background: #12121f;
                width: 10px;
                border: none;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #37474f;
                border-radius: 5px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover { background: #546e7a; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
            QScrollBar:horizontal {
                background: #12121f;
                height: 10px;
                border: none;
                margin: 0;
            }
            QScrollBar::handle:horizontal {
                background: #37474f;
                border-radius: 5px;
                min-width: 30px;
            }
            QScrollBar::handle:horizontal:hover { background: #546e7a; }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: none; }

            /* ── TextEdit / PlainTextEdit ── */
            QTextEdit, QPlainTextEdit {
                background: #0a0a14;
                border: 1px solid #303050;
                border-radius: 4px;
                color: #b0bec5;
                selection-background-color: #283593;
                selection-color: #ffffff;
            }

            /* ── ListView / TreeView / TableView ── */
            QListView, QListWidget {
                background: #12121f;
                border: 1px solid #303050;
                border-radius: 4px;
                color: #e0e0e0;
                outline: none;
            }
            QListView::item, QListWidget::item {
                padding: 4px 8px;
                border-radius: 3px;
            }
            QListView::item:selected, QListWidget::item:selected {
                background: #283593;
                color: #ffffff;
            }
            QListView::item:hover, QListWidget::item:hover {
                background: #1e1e38;
            }
            QTreeView, QTreeWidget {
                background: #12121f;
                border: 1px solid #303050;
                color: #e0e0e0;
                outline: none;
            }
            QTreeView::item:selected, QTreeWidget::item:selected {
                background: #283593;
                color: #ffffff;
            }
            QTreeView::item:hover, QTreeWidget::item:hover {
                background: #1e1e38;
            }
            QTableView, QTableWidget {
                background: #12121f;
                border: 1px solid #303050;
                color: #e0e0e0;
                gridline-color: #252545;
                outline: none;
            }
            QTableView::item:selected, QTableWidget::item:selected {
                background: #283593;
                color: #ffffff;
            }
            QHeaderView::section {
                background: #1a1a2e;
                color: #90caf9;
                border: 1px solid #303050;
                padding: 4px 8px;
                font-weight: bold;
            }

            /* ── Label ── */
            QLabel {
                color: #e0e0e0;
                background: transparent;
            }

            /* ── ProgressBar ── */
            QProgressBar {
                border: 1px solid #303050;
                border-radius: 4px;
                background: #1a1a2e;
                text-align: center;
                color: #ffffff;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: #2e7d32;
                border-radius: 3px;
            }

            /* ── Splitter ── */
            QSplitter::handle {
                background: #303050;
            }
            QSplitter::handle:horizontal { width: 2px; }
            QSplitter::handle:vertical { height: 2px; }

            /* ── Frame ── */
            QFrame {
                background: transparent;
            }
            QFrame[frameShape="4"], QFrame[frameShape="5"] {
                color: #303050;
            }

            /* ── Tooltip ── */
            QToolTip {
                background: #1a1a2e;
                color: #e0e0e0;
                border: 1px solid #5c6bc0;
                padding: 4px 8px;
            }

            /* ── StatusBar ── */
            QStatusBar {
                background: #0a0a14;
                color: #78909c;
                border-top: 1px solid #303050;
            }

            /* ── MenuBar ── */
            QMenuBar {
                background: #0f0f1a;
                color: #e0e0e0;
            }
            QMenuBar::item:selected { background: #1a1a2e; }
            QMenu {
                background: #1a1a2e;
                border: 1px solid #303050;
                color: #e0e0e0;
            }
            QMenu::item:selected { background: #283593; }
        """)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)

        # ── Left: Build Panel ──
        left_panel = QWidget()
        left_panel.setMinimumWidth(300)
        left_panel.setMaximumWidth(380)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(8)

        # Title
        title_label = QLabel("⚔️ FEGBA Randomizer")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #90caf9; padding: 4px;")
        left_layout.addWidget(title_label)

        # ROM Input
        rom_group = QGroupBox("ROM Input")
        rom_lay = QVBoxLayout(rom_group)

        self.rom_drop = ROMDropZone()
        rom_lay.addWidget(self.rom_drop)

        browse_row = QHBoxLayout()
        self.rom_path_edit = QLineEdit()
        self.rom_path_edit.setPlaceholderText("Path to .gba file...")
        self.rom_path_edit.setReadOnly(True)
        browse_row.addWidget(self.rom_path_edit)
        self.browse_btn = QPushButton("Browse")
        browse_row.addWidget(self.browse_btn)
        rom_lay.addLayout(browse_row)

        left_layout.addWidget(rom_group)

        # ROM Info
        self.rom_info_group = QGroupBox("ROM Info")
        info_lay = QVBoxLayout(self.rom_info_group)
        self.rom_title_label = QLabel("Title: —")
        self.rom_region_label = QLabel("Region: —")
        self.rom_tier_label = QLabel("Tier: —")
        self.rom_hash_label = QLabel("SHA-1: —")
        self.rom_hash_label.setWordWrap(True)
        self.rom_hash_label.setStyleSheet("font-size: 10px; color: #78909c;")
        self.copy_hash_btn = QToolButton()
        self.copy_hash_btn.setText("📋")
        self.copy_hash_btn.setToolTip("Copy hashes to clipboard")

        info_lay.addWidget(self.rom_title_label)
        info_lay.addWidget(self.rom_region_label)
        info_lay.addWidget(self.rom_tier_label)
        hash_row = QHBoxLayout()
        hash_row.addWidget(self.rom_hash_label, 1)
        hash_row.addWidget(self.copy_hash_btn)
        info_lay.addLayout(hash_row)
        self.rom_info_group.setVisible(False)
        left_layout.addWidget(self.rom_info_group)

        # Output Mode
        output_group = QGroupBox("Output")
        output_lay = QVBoxLayout(output_group)

        self.output_mode_group = QButtonGroup(self)
        mode_row = QHBoxLayout()
        self.radio_rom = QRadioButton("New ROM (.gba)")
        self.radio_bps = QRadioButton("BPS Patch")
        self.radio_ups = QRadioButton("UPS Patch")
        self.radio_rom.setChecked(True)
        self.output_mode_group.addButton(self.radio_rom, 0)
        self.output_mode_group.addButton(self.radio_bps, 1)
        self.output_mode_group.addButton(self.radio_ups, 2)
        mode_row.addWidget(self.radio_rom)
        mode_row.addWidget(self.radio_bps)
        mode_row.addWidget(self.radio_ups)
        output_lay.addLayout(mode_row)

        out_path_row = QHBoxLayout()
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setPlaceholderText("Output location...")
        out_path_row.addWidget(self.output_path_edit)
        self.output_browse_btn = QPushButton("📁")
        self.output_browse_btn.setMaximumWidth(36)
        out_path_row.addWidget(self.output_browse_btn)
        output_lay.addLayout(out_path_row)

        left_layout.addWidget(output_group)

        # Seed
        seed_group = QGroupBox("Seed")
        seed_lay = QHBoxLayout(seed_group)
        self.seed_edit = QLineEdit()
        self.seed_edit.setPlaceholderText("Enter seed or leave blank for random")
        seed_lay.addWidget(self.seed_edit)
        self.random_seed_btn = QPushButton("🎲")
        self.random_seed_btn.setMaximumWidth(36)
        self.random_seed_btn.setToolTip("Generate random seed")
        seed_lay.addWidget(self.random_seed_btn)
        self.copy_seed_btn = QPushButton("📋")
        self.copy_seed_btn.setMaximumWidth(36)
        self.copy_seed_btn.setToolTip("Copy seed")
        seed_lay.addWidget(self.copy_seed_btn)
        left_layout.addWidget(seed_group)

        # Presets
        preset_group = QGroupBox("Preset")
        preset_lay = QHBoxLayout(preset_group)
        self.preset_combo = QComboBox()
        self.preset_combo.addItem("— Select Preset —")
        for name in self.state.preset_manager.get_preset_names():
            self.preset_combo.addItem(name)
        preset_lay.addWidget(self.preset_combo)
        self.save_preset_btn = QPushButton("💾")
        self.save_preset_btn.setMaximumWidth(36)
        self.save_preset_btn.setToolTip("Save current settings as preset")
        preset_lay.addWidget(self.save_preset_btn)
        left_layout.addWidget(preset_group)

        # Settings string
        share_group = QGroupBox("Share Settings")
        share_lay = QHBoxLayout(share_group)
        self.settings_string_edit = QLineEdit()
        self.settings_string_edit.setPlaceholderText("Paste or copy settings string")
        share_lay.addWidget(self.settings_string_edit)
        self.copy_settings_btn = QPushButton("📋")
        self.copy_settings_btn.setMaximumWidth(36)
        self.copy_settings_btn.setToolTip("Copy settings string")
        share_lay.addWidget(self.copy_settings_btn)
        self.paste_settings_btn = QPushButton("📥")
        self.paste_settings_btn.setMaximumWidth(36)
        self.paste_settings_btn.setToolTip("Apply pasted settings string")
        share_lay.addWidget(self.paste_settings_btn)
        left_layout.addWidget(share_group)

        # Action buttons
        left_layout.addSpacing(8)
        self.preview_btn = QPushButton("👁  Preview")
        self.preview_btn.setObjectName("previewBtn")
        self.preview_btn.setEnabled(False)
        left_layout.addWidget(self.preview_btn)

        self.build_btn = QPushButton("⚙  BUILD")
        self.build_btn.setObjectName("buildBtn")
        self.build_btn.setEnabled(False)
        left_layout.addWidget(self.build_btn)

        self.open_folder_btn = QPushButton("📂 Open Output Folder")
        self.open_folder_btn.setEnabled(False)
        left_layout.addWidget(self.open_folder_btn)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        left_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-size: 11px; color: #b0bec5; padding: 2px; background: transparent;")
        left_layout.addWidget(self.status_label)

        left_layout.addStretch()

        # ── Right: Tabs ──
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(4, 8, 8, 8)

        self.tabs = QTabWidget()
        self.characters_tab = CharactersTab(self.state)
        self.classes_tab = ClassesTab(self.state)
        self.stats_tab = StatsTab(self.state)
        self.items_tab = ItemsTab(self.state)
        self.safety_tab = SafetyTab(self.state)
        self.advanced_tab = AdvancedTab(self.state)
        self.preview_tab = PreviewTab(self.state)
        self.logs_tab = LogsTab(self.state)

        self.tabs.addTab(self.characters_tab, "👤 Characters")
        self.tabs.addTab(self.classes_tab, "🛡 Classes")
        self.tabs.addTab(self.stats_tab, "📊 Stats")
        self.tabs.addTab(self.items_tab, "⚔ Items")
        self.tabs.addTab(self.safety_tab, "⚠ Safety")
        self.tabs.addTab(self.advanced_tab, "🔧 Advanced")
        self.tabs.addTab(self.preview_tab, "👁 Preview")
        self.tabs.addTab(self.logs_tab, "📜 Logs")

        right_layout.addWidget(self.tabs)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([340, 900])

        main_layout.addWidget(splitter)

    def _connect_signals(self):
        self.browse_btn.clicked.connect(self._browse_rom)
        self.rom_drop.rom_dropped.connect(self._load_rom)
        self.output_browse_btn.clicked.connect(self._browse_output)
        self.random_seed_btn.clicked.connect(self._generate_seed)
        self.copy_seed_btn.clicked.connect(self._copy_seed)
        self.copy_hash_btn.clicked.connect(self._copy_hash)
        self.preset_combo.currentIndexChanged.connect(self._apply_preset)
        self.copy_settings_btn.clicked.connect(self._copy_settings_string)
        self.paste_settings_btn.clicked.connect(self._paste_settings_string)
        self.preview_btn.clicked.connect(self._run_preview)
        self.build_btn.clicked.connect(self._run_build)
        self.open_folder_btn.clicked.connect(self._open_output_folder)

        # State signals
        self.state.rom_loaded.connect(self._on_rom_loaded)
        self.state.build_started.connect(self._on_build_started)
        self.state.build_progress.connect(self._on_build_progress)
        self.state.build_finished.connect(self._on_build_finished)
        self.state.preview_ready.connect(self._on_preview_ready)

    # ── Slots ──────────────────────────────────────────────────────

    def _browse_rom(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select GBA ROM", "",
            "GBA ROMs (*.gba);;All Files (*)"
        )
        if path:
            self._load_rom(path)

    def _load_rom(self, path: str):
        self.rom_path_edit.setText(path)
        self.status_label.setText("Loading ROM...")
        self.state.load_rom_async(path)

    def _on_rom_loaded(self, success: bool, message: str):
        if success:
            rom = self.state.rom
            profile = self.state.profile
            tier = self.state.tier

            self.rom_info_group.setVisible(True)
            self.rom_title_label.setText(f"Title: {profile.get('display_name', rom.gba_title)}")
            self.rom_region_label.setText(f"Region: {profile.get('region', '?')} | Game: {profile.get('game', '?').upper()}")

            tier_colors = {'A': '#4caf50', 'B': '#ff9800', 'C': '#f44336'}
            tier_text = {'A': '✅ Tier A — Verified', 'B': '⚡ Tier B — Recognized Hack', 'C': '⚠ Tier C — Unknown'}
            self.rom_tier_label.setText(tier_text.get(tier, f'Tier {tier}'))
            self.rom_tier_label.setStyleSheet(f"color: {tier_colors.get(tier, '#fff')}; font-weight: bold;")

            self.rom_hash_label.setText(f"SHA-1: {rom.sha1[:20]}...\nCRC32: {rom.crc32}")

            self.preview_btn.setEnabled(True)
            self.build_btn.setEnabled(True)
            self.status_label.setStyleSheet("font-size: 11px; color: #66bb6a; padding: 2px; background: transparent; font-weight: bold;")
            self.status_label.setText(f"✅ ROM loaded — {profile.get('display_name', 'Unknown')}")

            # Update tabs
            self.characters_tab.on_rom_loaded()
            self.classes_tab.on_rom_loaded()
            self.safety_tab.clear_issues()

            # Auto-generate output path
            from src.rom.writer import ROMWriter
            default_name = ROMWriter.generate_output_filename(rom.filename, "SEED")
            default_dir = os.path.dirname(self.state.rom_path)
            self.output_path_edit.setText(os.path.join(default_dir, default_name))
        else:
            self.status_label.setStyleSheet("font-size: 11px; color: #ef5350; padding: 2px; background: transparent; font-weight: bold;")
            self.status_label.setText(f"❌ {message}")
            QMessageBox.warning(self, "ROM Load Error", message)

    def _browse_output(self):
        mode = self.output_mode_group.checkedId()
        filters = {0: "GBA ROM (*.gba)", 1: "BPS Patch (*.bps)", 2: "UPS Patch (*.ups)"}
        path, _ = QFileDialog.getSaveFileName(
            self, "Select Output Location", "",
            f"{filters.get(mode, 'All Files (*)')}"
        )
        if path:
            self.output_path_edit.setText(path)

    def _generate_seed(self):
        from src.core.rng import RNGEngine
        seed = RNGEngine.generate_seed()
        self.seed_edit.setText(seed)

    def _copy_seed(self):
        QApplication.clipboard().setText(self.seed_edit.text())
        self.status_label.setText("Seed copied to clipboard.")

    def _copy_hash(self):
        if self.state.rom:
            text = f"SHA-1: {self.state.rom.sha1}\nCRC32: {self.state.rom.crc32}"
            QApplication.clipboard().setText(text)
            self.status_label.setText("Hashes copied to clipboard.")

    def _apply_preset(self, index):
        if index <= 0:
            return
        name = self.preset_combo.currentText()
        settings = self.state.preset_manager.apply_preset(name)
        if settings:
            self.state.settings = settings
            self.state.settings_changed.emit()
            self.status_label.setText(f"Preset '{name}' applied.")
            self._sync_ui_from_settings()

    def _copy_settings_string(self):
        from src.core.presets import PresetManager
        self._sync_settings_from_ui()
        profile_id = self.state.profile.get('profile_id', '') if self.state.profile else ''
        encoded = PresetManager.encode_settings_string(self.state.settings, profile_id)
        self.settings_string_edit.setText(encoded)
        QApplication.clipboard().setText(encoded)
        self.status_label.setText("Settings string copied to clipboard.")

    def _paste_settings_string(self):
        from src.core.presets import PresetManager
        text = self.settings_string_edit.text().strip()
        if not text:
            text = QApplication.clipboard().text().strip()
            self.settings_string_edit.setText(text)

        result = PresetManager.decode_settings_string(text)
        if result:
            self.state.settings = result['settings']
            self.state.settings_changed.emit()
            self._sync_ui_from_settings()
            self.status_label.setText("Settings applied from string.")
        else:
            QMessageBox.warning(self, "Invalid String", "Could not decode settings string.")

    def _run_preview(self):
        self._sync_settings_from_ui()
        self.status_label.setText("Generating preview...")
        self.state.run_preview_async()

    def _on_preview_ready(self):
        self.preview_tab.refresh()
        self.safety_tab.refresh()
        self.tabs.setCurrentWidget(self.preview_tab)
        self.status_label.setText("Preview generated.")

    def _run_build(self):
        self._sync_settings_from_ui()
        output_path = self.output_path_edit.text().strip()
        if not output_path:
            QMessageBox.warning(self, "No Output Path", "Please specify an output file location.")
            return

        seed = self.seed_edit.text().strip()
        mode_id = self.output_mode_group.checkedId()
        mode_map = {0: 'rom', 1: 'bps', 2: 'ups'}

        self.state.settings.output_path = output_path
        self.state.settings.seed = seed
        self.state.settings.output_mode = mode_map.get(mode_id, 'rom')

        self.status_label.setText("Building...")
        self.state.run_build_async()

    def _on_build_started(self):
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.build_btn.setEnabled(False)
        self.preview_btn.setEnabled(False)

    def _on_build_progress(self, value: int, message: str):
        self.progress_bar.setValue(value)
        self.status_label.setStyleSheet("font-size: 11px; color: #b0bec5; padding: 2px; background: transparent;")
        self.status_label.setText(message)

    def _on_build_finished(self, success: bool, message: str):
        self.progress_bar.setVisible(False)
        self.build_btn.setEnabled(True)
        self.preview_btn.setEnabled(True)

        if success:
            self.open_folder_btn.setEnabled(True)
            self.status_label.setStyleSheet("font-size: 11px; color: #66bb6a; padding: 2px; background: transparent; font-weight: bold;")
            self.status_label.setText(f"✅ {message}")
            self.logs_tab.refresh()
            QMessageBox.information(self, "Build Complete", message)
        else:
            self.status_label.setStyleSheet("font-size: 11px; color: #ef5350; padding: 2px; background: transparent; font-weight: bold;")
            self.status_label.setText(f"❌ {message}")
            self.safety_tab.refresh()
            QMessageBox.critical(self, "Build Failed", message)

    def _open_output_folder(self):
        path = self.output_path_edit.text().strip()
        if path:
            folder = os.path.dirname(path)
            if os.path.isdir(folder):
                os.startfile(folder) if sys.platform == 'win32' else os.system(f'xdg-open "{folder}"')

    def _sync_settings_from_ui(self):
        """Pull current settings from all tabs into state.settings."""
        self.stats_tab.sync_to_settings()
        self.classes_tab.sync_to_settings()
        self.items_tab.sync_to_settings()
        self.advanced_tab.sync_to_settings()
        self.characters_tab.sync_to_settings()

    def _sync_ui_from_settings(self):
        """Push state.settings into all tab UIs."""
        self.stats_tab.sync_from_settings()
        self.classes_tab.sync_from_settings()
        self.items_tab.sync_from_settings()
        self.advanced_tab.sync_from_settings()
        self.characters_tab.sync_from_settings()