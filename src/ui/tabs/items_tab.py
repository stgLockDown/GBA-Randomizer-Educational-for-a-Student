"""
Items Tab: inventory randomization options.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QComboBox,
    QLabel, QRadioButton, QButtonGroup, QTextEdit
)
from PySide6.QtCore import Qt


class ItemsTab(QWidget):
    def __init__(self, app_state, parent=None):
        super().__init__(parent)
        self.state = app_state
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Inventory mode
        mode_group = QGroupBox("Starting Inventory Randomization")
        mode_layout = QVBoxLayout(mode_group)

        self.mode_btn_group = QButtonGroup(self)

        modes = [
            ("dont_change", "Don't Change (default safe)",
             "Keep all starting items exactly as they are. Safest option."),
            ("guarantee_usable", "Guarantee Usable Weapon Only",
             "Ensure each character has at least one weapon they can use. Minimal changes."),
            ("random_consumables", "Randomize Consumables Only",
             "Keep weapons but shuffle healing items, keys, and other consumables."),
            ("full_random", "Full Random (Advanced)",
             "Randomize all inventory slots. May produce odd loadouts. Use blacklist to exclude dangerous items."),
        ]

        for i, (key, label, desc) in enumerate(modes):
            radio = QRadioButton(label)
            radio.setToolTip(desc)
            if i == 0:
                radio.setChecked(True)
            self.mode_btn_group.addButton(radio, i)
            mode_layout.addWidget(radio)

            desc_label = QLabel(desc)
            desc_label.setStyleSheet("color: #78909c; font-size: 11px; margin-left: 24px; margin-bottom: 6px;")
            desc_label.setWordWrap(True)
            mode_layout.addWidget(desc_label)

        layout.addWidget(mode_group)

        # Blacklist
        blacklist_group = QGroupBox("Item Blacklist (for Full Random mode)")
        bl_layout = QVBoxLayout(blacklist_group)

        bl_desc = QLabel(
            "Enter item IDs to exclude from random inventory (one per line). "
            "Useful for preventing story-critical or overpowered items from appearing."
        )
        bl_desc.setWordWrap(True)
        bl_desc.setStyleSheet("color: #90a4ae; font-size: 11px; margin-bottom: 4px;")
        bl_layout.addWidget(bl_desc)

        self.blacklist_edit = QTextEdit()
        self.blacklist_edit.setPlaceholderText("e.g.\n100\n150\n200")
        self.blacklist_edit.setMaximumHeight(120)
        self.blacklist_edit.setStyleSheet("""
            QTextEdit {
                background: #1a1a2e;
                border: 1px solid #303050;
                border-radius: 4px;
                padding: 4px;
                color: #e0e0e0;
                font-family: monospace;
            }
        """)
        bl_layout.addWidget(self.blacklist_edit)
        layout.addWidget(blacklist_group)

        # Info panel
        info_group = QGroupBox("ℹ Notes")
        info_layout = QVBoxLayout(info_group)
        info_text = QLabel(
            "• Weapon usability is checked by the Safety validator after randomization.\n"
            "• If a character ends up with no usable weapon, the auto-fix system will "
            "raise their weapon rank (if enabled in Stats tab) or flag it in the Safety tab.\n"
            "• The 'Guarantee Usable Weapon' mode only ensures slot 1 has a usable weapon; "
            "other slots are untouched.\n"
            "• Items marked in the blacklist will never appear in any character's starting inventory."
        )
        info_text.setWordWrap(True)
        info_text.setStyleSheet("color: #78909c; font-size: 11px;")
        info_layout.addWidget(info_text)
        layout.addWidget(info_group)

        layout.addStretch()

    def sync_to_settings(self):
        s = self.state.settings
        mode_map = {0: "dont_change", 1: "guarantee_usable", 2: "random_consumables", 3: "full_random"}
        checked_id = self.mode_btn_group.checkedId()
        s.inventory_mode = mode_map.get(checked_id, "dont_change")

        # Parse blacklist
        text = self.blacklist_edit.toPlainText().strip()
        ids = []
        for line in text.split('\n'):
            line = line.strip()
            if line.isdigit():
                ids.append(int(line))
        s.inventory_blacklist_ids = ids

    def sync_from_settings(self):
        s = self.state.settings
        mode_map = {"dont_change": 0, "guarantee_usable": 1, "random_consumables": 2, "full_random": 3}
        btn_id = mode_map.get(s.inventory_mode, 0)
        btn = self.mode_btn_group.button(btn_id)
        if btn:
            btn.setChecked(True)

        if s.inventory_blacklist_ids:
            self.blacklist_edit.setPlainText('\n'.join(str(i) for i in s.inventory_blacklist_ids))