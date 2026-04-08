"""
Preview Tab: before/after comparison table with filters and color coding.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QCheckBox, QTreeWidget, QTreeWidgetItem, QHeaderView,
    QGroupBox, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush, QPixmap, QIcon


class PreviewTab(QWidget):
    def __init__(self, app_state, parent=None):
        super().__init__(parent)
        self.state = app_state
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Filter bar
        filter_frame = QFrame()
        filter_frame.setStyleSheet("""
            QFrame {
                background: #1a1a2e;
                border: 1px solid #303050;
                border-radius: 6px;
                padding: 6px;
            }
        """)
        filter_layout = QHBoxLayout(filter_frame)

        filter_layout.addWidget(QLabel("🔍"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search by name...")
        self.search_edit.textChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.search_edit)

        self.changed_only_check = QCheckBox("Changed only")
        self.changed_only_check.stateChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.changed_only_check)

        self.lords_only_check = QCheckBox("Lords only")
        self.lords_only_check.stateChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.lords_only_check)

        self.staff_check = QCheckBox("Staff-capable")
        self.staff_check.stateChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.staff_check)

        layout.addWidget(filter_frame)

        # Summary
        self.summary_label = QLabel("Run Preview to see changes.")
        self.summary_label.setStyleSheet("color: #78909c; font-size: 12px; padding: 4px;")
        layout.addWidget(self.summary_label)

        # Preview table
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([
            "Name", "Old Class", "New Class",
            "Base Δ", "Growth Δ", "Rank Changes", "Flags"
        ])
        self.tree.setColumnWidth(0, 130)
        self.tree.setColumnWidth(1, 80)
        self.tree.setColumnWidth(2, 80)
        self.tree.setColumnWidth(3, 200)
        self.tree.setColumnWidth(4, 200)
        self.tree.setColumnWidth(5, 160)
        self.tree.setColumnWidth(6, 100)
        self.tree.setAlternatingRowColors(True)
        self.tree.setRootIsDecorated(False)
        self.tree.setSortingEnabled(True)
        self.tree.setStyleSheet("""
            QTreeWidget {
                background: #12121f;
                border: 1px solid #303050;
                border-radius: 4px;
                alternate-background-color: #151528;
            }
            QTreeWidget::item {
                padding: 3px 4px;
            }
            QHeaderView::section {
                background: #1a1a2e;
                border: 1px solid #303050;
                padding: 4px 8px;
                color: #90a4ae;
                font-weight: bold;
                font-size: 11px;
            }
        """)
        layout.addWidget(self.tree, 1)

        # Color legend
        legend_layout = QHBoxLayout()
        legend_layout.addWidget(self._legend_swatch("#66bb6a", "Buff"))
        legend_layout.addWidget(self._legend_swatch("#ef5350", "Nerf"))
        legend_layout.addWidget(self._legend_swatch("#78909c", "Unchanged"))
        legend_layout.addWidget(self._legend_swatch("#42a5f5", "Locked"))
        legend_layout.addStretch()
        layout.addLayout(legend_layout)

    def _legend_swatch(self, color: str, text: str) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 8, 0)
        swatch = QLabel("■")
        swatch.setStyleSheet(f"color: {color}; font-size: 14px;")
        lay.addWidget(swatch)
        label = QLabel(text)
        label.setStyleSheet("color: #90a4ae; font-size: 11px;")
        lay.addWidget(label)
        return w

    def refresh(self):
        """Refresh the preview table from app state."""
        self.tree.clear()
        changes = self.state.preview_changes

        if not changes:
            self.summary_label.setText("No preview data. Click Preview on the left panel.")
            return

        changed_count = sum(1 for c in changes if
                           c.old_class_id != c.new_class_id or
                           c.old_bases != c.new_bases or
                           c.old_growths != c.new_growths or
                           c.old_ranks != c.new_ranks)
        self.summary_label.setText(
            f"📊 {len(changes)} characters | {changed_count} modified | "
            f"Seed: {self.state.settings.seed}"
        )

        green = QBrush(QColor("#66bb6a"))
        red = QBrush(QColor("#ef5350"))
        grey = QBrush(QColor("#78909c"))
        blue = QBrush(QColor("#42a5f5"))

        char_meta = self.state.profile.get('characters', {}) if self.state.profile else {}
        rules = self.state.profile.get('rules', {}) if self.state.profile else {}
        lord_ids = set(rules.get('lord_character_ids', []))

        for ch in changes:
            item = QTreeWidgetItem()

            # Name
            item.setText(0, ch.name)
            item.setData(0, Qt.UserRole, ch.char_id)
            item.setData(0, Qt.UserRole + 1, ch)  # Store full change object

            # Classes
            item.setText(1, str(ch.old_class_id))
            item.setText(2, str(ch.new_class_id))
            if ch.old_class_id != ch.new_class_id:
                item.setForeground(2, green)
            else:
                item.setForeground(2, grey)

            # Base deltas
            base_delta_str = self._format_deltas(ch.old_bases, ch.new_bases)
            item.setText(3, base_delta_str)
            base_sum = sum(ch.new_bases.get(k, 0) - ch.old_bases.get(k, 0) for k in ch.old_bases)
            if base_sum > 0:
                item.setForeground(3, green)
            elif base_sum < 0:
                item.setForeground(3, red)
            else:
                item.setForeground(3, grey)

            # Growth deltas
            growth_delta_str = self._format_deltas(ch.old_growths, ch.new_growths)
            item.setText(4, growth_delta_str)
            growth_sum = sum(ch.new_growths.get(k, 0) - ch.old_growths.get(k, 0) for k in ch.old_growths)
            if growth_sum > 0:
                item.setForeground(4, green)
            elif growth_sum < 0:
                item.setForeground(4, red)
            else:
                item.setForeground(4, grey)

            # Rank changes
            rank_changes = []
            for k in ch.old_ranks:
                old_v = ch.old_ranks.get(k, 0)
                new_v = ch.new_ranks.get(k, 0)
                if old_v != new_v:
                    short = k.split('_')[-1][:3].upper()
                    rank_changes.append(f"{short}:{old_v}→{new_v}")
            item.setText(5, " ".join(rank_changes) if rank_changes else "—")

            # Flags
            flags = []
            if ch.is_locked:
                flags.append("🔒LOCKED")
                item.setForeground(0, blue)
            if ch.is_excluded:
                flags.append("🚫EXCL")
            if ch.char_id in lord_ids:
                flags.append("👑LORD")
            item.setText(6, " ".join(flags))

            self.tree.addTopLevelItem(item)

        self._apply_filters()

    def _format_deltas(self, old: dict, new: dict) -> str:
        parts = []
        for key in old:
            o = old.get(key, 0)
            n = new.get(key, 0)
            diff = n - o
            if diff != 0:
                short = key.split('_')[-1][:3].upper()
                sign = "+" if diff > 0 else ""
                parts.append(f"{short}{sign}{diff}")
        return " ".join(parts) if parts else "—"

    def _apply_filters(self):
        """Apply search and filter checkboxes to the tree."""
        search_text = self.search_edit.text().strip().lower()
        changed_only = self.changed_only_check.isChecked()
        lords_only = self.lords_only_check.isChecked()
        staff_only = self.staff_check.isChecked()

        rules = self.state.profile.get('rules', {}) if self.state.profile else {}
        lord_ids = set(rules.get('lord_character_ids', []))

        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            ch = item.data(0, Qt.UserRole + 1)
            char_id = item.data(0, Qt.UserRole)

            show = True

            # Search filter
            if search_text and search_text not in item.text(0).lower():
                show = False

            # Changed only
            if changed_only and ch:
                is_changed = (ch.old_class_id != ch.new_class_id or
                              ch.old_bases != ch.new_bases or
                              ch.old_growths != ch.new_growths or
                              ch.old_ranks != ch.new_ranks)
                if not is_changed:
                    show = False

            # Lords only
            if lords_only and char_id not in lord_ids:
                show = False

            # Staff capable
            if staff_only and ch:
                has_staff = ch.new_ranks.get('rank_staff', 0) > 0
                if not has_staff:
                    show = False

            item.setHidden(not show)