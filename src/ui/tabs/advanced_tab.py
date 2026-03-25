"""
Advanced Tab: force build, tier C options, and advanced settings.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QCheckBox,
    QLabel, QFrame
)
from PySide6.QtCore import Qt


class AdvancedTab(QWidget):
    def __init__(self, app_state, parent=None):
        super().__init__(parent)
        self.state = app_state
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Warning banner
        warning_frame = QFrame()
        warning_frame.setStyleSheet("""
            QFrame {
                background: #3e2723;
                border: 1px solid #bf360c;
                border-radius: 6px;
                padding: 12px;
            }
        """)
        warning_layout = QVBoxLayout(warning_frame)
        warning_label = QLabel(
            "⚠️ ADVANCED SETTINGS\n\n"
            "These options can produce broken ROMs or unexpected behavior. "
            "Use only if you understand the implications."
        )
        warning_label.setWordWrap(True)
        warning_label.setStyleSheet("color: #ffab91; font-weight: bold;")
        warning_layout.addWidget(warning_label)
        layout.addWidget(warning_frame)

        # Build overrides
        build_group = QGroupBox("Build Overrides")
        build_layout = QVBoxLayout(build_group)

        self.force_build_check = QCheckBox("Force Build (ignore all validation errors)")
        self.force_build_check.setStyleSheet("color: #ef5350; font-weight: bold;")
        self.force_build_check.setToolTip(
            "If enabled, the build will proceed even if there are validation errors.\n"
            "The resulting ROM may crash or have broken gameplay."
        )
        build_layout.addWidget(self.force_build_check)

        force_desc = QLabel(
            "Normally the build is blocked when validation errors are found (e.g., invalid class IDs, "
            "unusable weapons). Enabling Force Build bypasses all error checks and outputs the ROM "
            "regardless. Warnings will still be logged."
        )
        force_desc.setWordWrap(True)
        force_desc.setStyleSheet("color: #78909c; font-size: 11px; margin-left: 24px;")
        build_layout.addWidget(force_desc)

        self.auto_fix_check = QCheckBox("Auto-fix minor issues (recommended)")
        self.auto_fix_check.setChecked(True)
        self.auto_fix_check.setToolTip(
            "Automatically correct minor issues such as:\n"
            "• Weapon ranks below minimum for starting weapon\n"
            "• Stat values out of normal bounds\n"
            "• Invalid class assignments (reverted to original)"
        )
        build_layout.addWidget(self.auto_fix_check)

        layout.addWidget(build_group)

        # Tier C options
        tierc_group = QGroupBox("Tier C (Unrecognized ROM) Options")
        tierc_layout = QVBoxLayout(tierc_group)

        tierc_desc = QLabel(
            "When a ROM is not in the verified database (Tier C), only limited features "
            "are enabled by default. These options let you force-enable modules at your own risk."
        )
        tierc_desc.setWordWrap(True)
        tierc_desc.setStyleSheet("color: #90a4ae; font-size: 11px; margin-bottom: 8px;")
        tierc_layout.addWidget(tierc_desc)

        self.tierc_force_class = QCheckBox("Force-enable class randomization on Tier C ROMs")
        self.tierc_force_bases = QCheckBox("Force-enable bases randomization on Tier C ROMs")
        self.tierc_force_growths = QCheckBox("Force-enable growths randomization on Tier C ROMs")
        self.tierc_force_ranks = QCheckBox("Force-enable ranks randomization on Tier C ROMs")
        self.tierc_force_inventory = QCheckBox("Force-enable inventory randomization on Tier C ROMs")

        for cb in [self.tierc_force_class, self.tierc_force_bases,
                    self.tierc_force_growths, self.tierc_force_ranks,
                    self.tierc_force_inventory]:
            cb.setStyleSheet("color: #ffb74d;")
            tierc_layout.addWidget(cb)

        layout.addWidget(tierc_group)

        # Patch verification
        patch_group = QGroupBox("Patch Options")
        patch_layout = QVBoxLayout(patch_group)

        self.verify_patch_check = QCheckBox("Verify patch after generation (applies patch in-memory and compares)")
        self.verify_patch_check.setChecked(True)
        self.verify_patch_check.setToolTip(
            "After generating a BPS/UPS patch, the tool will apply it to the original ROM in memory "
            "and verify the result matches the modified ROM. This catches rare patch generation bugs."
        )
        patch_layout.addWidget(self.verify_patch_check)

        layout.addWidget(patch_group)

        # Debug
        debug_group = QGroupBox("Debug")
        debug_layout = QVBoxLayout(debug_group)

        self.verbose_log_check = QCheckBox("Generate verbose spoiler log (includes all characters, not just changed)")
        debug_layout.addWidget(self.verbose_log_check)

        self.json_log_check = QCheckBox("Generate JSON spoiler log (in addition to text)")
        self.json_log_check.setChecked(True)
        debug_layout.addWidget(self.json_log_check)

        layout.addWidget(debug_group)
        layout.addStretch()

    def sync_to_settings(self):
        s = self.state.settings
        s.force_build = self.force_build_check.isChecked()
        s.auto_fix = self.auto_fix_check.isChecked()

    def sync_from_settings(self):
        s = self.state.settings
        self.force_build_check.setChecked(s.force_build)
        self.auto_fix_check.setChecked(s.auto_fix)