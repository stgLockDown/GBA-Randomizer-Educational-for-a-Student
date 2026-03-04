"""
Stats Tab: bases and growths randomization modes and sliders.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QComboBox,
    QCheckBox, QLabel, QSpinBox, QSlider, QGridLayout, QFrame
)
from PySide6.QtCore import Qt


class StatSliderRow(QWidget):
    """A labeled slider with value display."""
    def __init__(self, label_text: str, min_val: int, max_val: int, default: int, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel(label_text)
        self.label.setMinimumWidth(120)
        self.label.setStyleSheet("color: #b0bec5;")
        layout.addWidget(self.label)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(min_val, max_val)
        self.slider.setValue(default)
        layout.addWidget(self.slider, 1)

        self.value_label = QLabel(str(default))
        self.value_label.setMinimumWidth(36)
        self.value_label.setAlignment(Qt.AlignCenter)
        self.value_label.setStyleSheet("color: #90caf9; font-weight: bold;")
        layout.addWidget(self.value_label)

        self.slider.valueChanged.connect(lambda v: self.value_label.setText(str(v)))

    def value(self) -> int:
        return self.slider.value()

    def setValue(self, v: int):
        self.slider.setValue(v)


class StatsTab(QWidget):
    def __init__(self, app_state, parent=None):
        super().__init__(parent)
        self.state = app_state
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # ── Bases ──
        bases_group = QGroupBox("Base Stats Randomization")
        bases_layout = QVBoxLayout(bases_group)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Mode:"))
        self.bases_mode = QComboBox()
        self.bases_mode.addItems(["Vanilla (No Change)", "Shuffle Among Characters", "Randomize (±Variance)"])
        mode_row.addWidget(self.bases_mode, 1)
        bases_layout.addLayout(mode_row)

        self.bases_variance_slider = StatSliderRow("Variance (±):", 0, 15, 3)
        bases_layout.addWidget(self.bases_variance_slider)

        range_row = QHBoxLayout()
        range_row.addWidget(QLabel("Min:"))
        self.bases_min_spin = QSpinBox()
        self.bases_min_spin.setRange(-20, 60)
        self.bases_min_spin.setValue(0)
        range_row.addWidget(self.bases_min_spin)
        range_row.addSpacing(16)
        range_row.addWidget(QLabel("Max:"))
        self.bases_max_spin = QSpinBox()
        self.bases_max_spin.setRange(0, 60)
        self.bases_max_spin.setValue(30)
        range_row.addWidget(self.bases_max_spin)
        range_row.addStretch()
        bases_layout.addLayout(range_row)

        self.bases_preserve_check = QCheckBox("Preserve total base stat sum (budget mode)")
        bases_layout.addWidget(self.bases_preserve_check)

        layout.addWidget(bases_group)

        # ── Growths ──
        growths_group = QGroupBox("Growth Rates Randomization")
        growths_layout = QVBoxLayout(growths_group)

        gmode_row = QHBoxLayout()
        gmode_row.addWidget(QLabel("Mode:"))
        self.growths_mode = QComboBox()
        self.growths_mode.addItems(["Vanilla (No Change)", "Shuffle Among Characters", "Randomize (±Variance)"])
        gmode_row.addWidget(self.growths_mode, 1)
        growths_layout.addLayout(gmode_row)

        self.growths_variance_slider = StatSliderRow("Variance (±):", 0, 80, 20)
        growths_layout.addWidget(self.growths_variance_slider)

        grange_row = QHBoxLayout()
        grange_row.addWidget(QLabel("Min:"))
        self.growths_min_spin = QSpinBox()
        self.growths_min_spin.setRange(0, 100)
        self.growths_min_spin.setValue(5)
        grange_row.addWidget(self.growths_min_spin)
        grange_row.addSpacing(16)
        grange_row.addWidget(QLabel("Max:"))
        self.growths_max_spin = QSpinBox()
        self.growths_max_spin.setRange(10, 255)
        self.growths_max_spin.setValue(100)
        grange_row.addWidget(self.growths_max_spin)
        grange_row.addStretch()
        growths_layout.addLayout(grange_row)

        self.growths_preserve_check = QCheckBox("Preserve total growth sum (budget mode)")
        growths_layout.addWidget(self.growths_preserve_check)

        layout.addWidget(growths_group)

        # ── Weapon Ranks ──
        ranks_group = QGroupBox("Weapon Ranks Randomization")
        ranks_layout = QVBoxLayout(ranks_group)

        rmode_row = QHBoxLayout()
        rmode_row.addWidget(QLabel("Mode:"))
        self.ranks_mode = QComboBox()
        self.ranks_mode.addItems(["Vanilla (No Change)", "Shuffle Among Characters", "Randomize (±Variance)"])
        rmode_row.addWidget(self.ranks_mode, 1)
        ranks_layout.addLayout(rmode_row)

        self.ranks_variance_slider = StatSliderRow("Variance (±):", 0, 120, 30)
        ranks_layout.addWidget(self.ranks_variance_slider)

        fix_row = QHBoxLayout()
        fix_row.addWidget(QLabel("Weapon usability fix:"))
        self.ranks_fix_combo = QComboBox()
        self.ranks_fix_combo.addItems([
            "Auto-raise rank to minimum",
            "Swap starting weapon to match rank",
            "No fix (may cause unusable weapons)"
        ])
        fix_row.addWidget(self.ranks_fix_combo, 1)
        ranks_layout.addLayout(fix_row)

        layout.addWidget(ranks_group)
        layout.addStretch()

    def sync_to_settings(self):
        s = self.state.settings
        mode_map = {0: "vanilla", 1: "shuffle", 2: "random"}

        s.bases_mode = mode_map.get(self.bases_mode.currentIndex(), "vanilla")
        s.bases_variance = self.bases_variance_slider.value()
        s.bases_min = self.bases_min_spin.value()
        s.bases_max = self.bases_max_spin.value()
        s.bases_preserve_total = self.bases_preserve_check.isChecked()

        s.growths_mode = mode_map.get(self.growths_mode.currentIndex(), "vanilla")
        s.growths_variance = self.growths_variance_slider.value()
        s.growths_min = self.growths_min_spin.value()
        s.growths_max = self.growths_max_spin.value()
        s.growths_preserve_total = self.growths_preserve_check.isChecked()

        s.ranks_mode = mode_map.get(self.ranks_mode.currentIndex(), "vanilla")
        s.ranks_variance = self.ranks_variance_slider.value()

        fix_map = {0: "raise_rank", 1: "swap_weapon", 2: "none"}
        s.ranks_fix_weapon = fix_map.get(self.ranks_fix_combo.currentIndex(), "raise_rank")

    def sync_from_settings(self):
        s = self.state.settings
        mode_map = {"vanilla": 0, "shuffle": 1, "random": 2}

        self.bases_mode.setCurrentIndex(mode_map.get(s.bases_mode, 0))
        self.bases_variance_slider.setValue(s.bases_variance)
        self.bases_min_spin.setValue(s.bases_min)
        self.bases_max_spin.setValue(s.bases_max)
        self.bases_preserve_check.setChecked(s.bases_preserve_total)

        self.growths_mode.setCurrentIndex(mode_map.get(s.growths_mode, 0))
        self.growths_variance_slider.setValue(s.growths_variance)
        self.growths_min_spin.setValue(s.growths_min)
        self.growths_max_spin.setValue(s.growths_max)
        self.growths_preserve_check.setChecked(s.growths_preserve_total)

        self.ranks_mode.setCurrentIndex(mode_map.get(s.ranks_mode, 0))
        self.ranks_variance_slider.setValue(s.ranks_variance)

        fix_map = {"raise_rank": 0, "swap_weapon": 1, "none": 2}
        self.ranks_fix_combo.setCurrentIndex(fix_map.get(s.ranks_fix_weapon, 0))