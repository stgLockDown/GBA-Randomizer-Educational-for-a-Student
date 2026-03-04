"""
Classes Tab: class pool checklist, weights, and mode selection.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QComboBox,
    QCheckBox, QLabel, QSpinBox, QScrollArea, QGridLayout,
    QFrame, QPushButton
)
from PySide6.QtCore import Qt


class ClassesTab(QWidget):
    def __init__(self, app_state, parent=None):
        super().__init__(parent)
        self.state = app_state
        self._class_checks = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Mode selection
        mode_group = QGroupBox("Class Randomization Mode")
        mode_layout = QHBoxLayout(mode_group)

        mode_layout.addWidget(QLabel("Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Vanilla (No Change)", "Shuffle", "Random"])
        mode_layout.addWidget(self.mode_combo, 1)
        layout.addWidget(mode_group)

        # Constraints
        constraints_group = QGroupBox("Constraints")
        constraints_layout = QGridLayout(constraints_group)

        self.keep_lords_check = QCheckBox("Keep Lords in lord classes")
        self.keep_lords_check.setChecked(True)
        self.keep_thieves_check = QCheckBox("Keep Thieves as thieves")
        self.keep_thieves_check.setChecked(True)
        self.keep_dancers_check = QCheckBox("Keep Dancers/Bards")
        self.keep_dancers_check.setChecked(True)
        self.respect_gender_check = QCheckBox("Respect gender locks")
        self.respect_gender_check.setChecked(True)
        self.exclude_monsters_check = QCheckBox("Exclude monster classes (FE8)")
        self.exclude_monsters_check.setChecked(True)

        constraints_layout.addWidget(self.keep_lords_check, 0, 0)
        constraints_layout.addWidget(self.keep_thieves_check, 0, 1)
        constraints_layout.addWidget(self.keep_dancers_check, 1, 0)
        constraints_layout.addWidget(self.respect_gender_check, 1, 1)
        constraints_layout.addWidget(self.exclude_monsters_check, 2, 0)

        # Max copies
        copies_row = QHBoxLayout()
        copies_row.addWidget(QLabel("Max copies per class (0 = unlimited):"))
        self.max_copies_spin = QSpinBox()
        self.max_copies_spin.setRange(0, 20)
        self.max_copies_spin.setValue(0)
        copies_row.addWidget(self.max_copies_spin)
        copies_row.addStretch()
        constraints_layout.addLayout(copies_row, 3, 0, 1, 2)

        layout.addWidget(constraints_group)

        # Class pool
        pool_group = QGroupBox("Allowed Class Pool (checked = allowed)")
        pool_outer = QVBoxLayout(pool_group)

        btn_row = QHBoxLayout()
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self._select_all)
        self.deselect_all_btn = QPushButton("Deselect All")
        self.deselect_all_btn.clicked.connect(self._deselect_all)
        btn_row.addWidget(self.select_all_btn)
        btn_row.addWidget(self.deselect_all_btn)
        btn_row.addStretch()
        pool_outer.addLayout(btn_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        self.pool_widget = QWidget()
        self.pool_layout = QGridLayout(self.pool_widget)
        self.pool_layout.setSpacing(4)

        # Placeholder — populated when ROM is loaded
        self.pool_placeholder = QLabel("Load a ROM to see available classes.")
        self.pool_placeholder.setStyleSheet("color: #78909c; padding: 20px;")
        self.pool_placeholder.setAlignment(Qt.AlignCenter)
        self.pool_layout.addWidget(self.pool_placeholder, 0, 0, 1, 4)

        scroll.setWidget(self.pool_widget)
        pool_outer.addWidget(scroll)
        layout.addWidget(pool_group, 1)

    def on_rom_loaded(self):
        """Populate class pool from loaded ROM profile."""
        # Clear existing
        while self.pool_layout.count():
            item = self.pool_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._class_checks.clear()

        class_table = self.state.table_manager.tables.get('classes') if self.state.table_manager else None
        if not class_table:
            return

        col_count = 3
        for i, entry in enumerate(class_table):
            class_id = entry.get('class_id', entry.index)
            if class_id == 0:
                continue

            name = f"Class {class_id}"
            # Try to get a readable name from class type info
            gender_flag = entry.get('gender_flag', 2)
            gender_str = ""
            if gender_flag == 0:
                gender_str = " ♂"
            elif gender_flag == 1:
                gender_str = " ♀"

            cb = QCheckBox(f"[{class_id:3d}] {name}{gender_str}")
            cb.setChecked(True)
            cb.setStyleSheet("font-size: 11px;")

            row, col = divmod(i, col_count)
            self.pool_layout.addWidget(cb, row, col)
            self._class_checks[class_id] = cb

    def _select_all(self):
        for cb in self._class_checks.values():
            cb.setChecked(True)

    def _deselect_all(self):
        for cb in self._class_checks.values():
            cb.setChecked(False)

    def sync_to_settings(self):
        """Push UI values to settings."""
        mode_map = {0: "vanilla", 1: "shuffle", 2: "random"}
        self.state.settings.class_mode = mode_map.get(self.mode_combo.currentIndex(), "vanilla")
        self.state.settings.keep_lords = self.keep_lords_check.isChecked()
        self.state.settings.keep_thieves = self.keep_thieves_check.isChecked()
        self.state.settings.keep_dancers = self.keep_dancers_check.isChecked()
        self.state.settings.respect_gender = self.respect_gender_check.isChecked()
        self.state.settings.exclude_monsters = self.exclude_monsters_check.isChecked()
        self.state.settings.max_class_copies = self.max_copies_spin.value()

        # Collect allowed class IDs
        allowed = [cid for cid, cb in self._class_checks.items() if cb.isChecked()]
        self.state.settings.allowed_class_ids = allowed

    def sync_from_settings(self):
        """Pull settings values to UI."""
        s = self.state.settings
        mode_map = {"vanilla": 0, "shuffle": 1, "random": 2}
        self.mode_combo.setCurrentIndex(mode_map.get(s.class_mode, 0))
        self.keep_lords_check.setChecked(s.keep_lords)
        self.keep_thieves_check.setChecked(s.keep_thieves)
        self.keep_dancers_check.setChecked(s.keep_dancers)
        self.respect_gender_check.setChecked(s.respect_gender)
        self.exclude_monsters_check.setChecked(s.exclude_monsters)
        self.max_copies_spin.setValue(s.max_class_copies)

        if s.allowed_class_ids:
            allowed_set = set(s.allowed_class_ids)
            for cid, cb in self._class_checks.items():
                cb.setChecked(cid in allowed_set)