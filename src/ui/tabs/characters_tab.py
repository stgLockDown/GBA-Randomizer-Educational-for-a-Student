"""
Characters Tab: portrait list with detail panel and per-character locks.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QGroupBox, QCheckBox, QScrollArea, QFrame, QGridLayout,
    QSplitter, QSizePolicy
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QIcon, QColor


class CharactersTab(QWidget):
    def __init__(self, app_state, parent=None):
        super().__init__(parent)
        self.state = app_state
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        splitter = QSplitter(Qt.Horizontal)

        # ── Left: Character list ──
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        list_label = QLabel("Characters")
        list_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #90caf9; padding: 4px;")
        left_layout.addWidget(list_label)

        self.char_list = QListWidget()
        self.char_list.setIconSize(QSize(32, 32))
        self.char_list.setSpacing(2)
        self.char_list.setStyleSheet("""
            QListWidget {
                background: #12121f;
                border: 1px solid #303050;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 4px 8px;
                border-radius: 3px;
            }
            QListWidget::item:selected {
                background: #283593;
            }
            QListWidget::item:hover {
                background: #1e1e38;
            }
        """)
        self.char_list.currentRowChanged.connect(self._on_char_selected)
        left_layout.addWidget(self.char_list)

        # ── Right: Detail panel ──
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(4, 0, 0, 0)

        # Portrait + name header
        header = QHBoxLayout()
        self.portrait_label = QLabel()
        self.portrait_label.setFixedSize(64, 64)
        self.portrait_label.setStyleSheet("""
            border: 2px solid #303050;
            border-radius: 4px;
            background: #1a1a2e;
        """)
        self.portrait_label.setAlignment(Qt.AlignCenter)
        self.portrait_label.setText("?")
        header.addWidget(self.portrait_label)

        name_col = QVBoxLayout()
        self.name_label = QLabel("Select a character")
        self.name_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #e0e0e0;")
        name_col.addWidget(self.name_label)
        self.role_label = QLabel("")
        self.role_label.setStyleSheet("font-size: 11px; color: #78909c;")
        name_col.addWidget(self.role_label)
        header.addLayout(name_col, 1)
        right_layout.addLayout(header)

        # Lock toggles
        lock_group = QGroupBox("Randomization Locks")
        lock_layout = QGridLayout(lock_group)
        self.lock_class = QCheckBox("Lock Class")
        self.lock_bases = QCheckBox("Lock Bases")
        self.lock_growths = QCheckBox("Lock Growths")
        self.lock_ranks = QCheckBox("Lock Ranks")
        self.lock_items = QCheckBox("Lock Items")
        self.exclude_check = QCheckBox("Exclude from ALL randomization")
        self.exclude_check.setStyleSheet("color: #ef5350;")

        lock_layout.addWidget(self.lock_class, 0, 0)
        lock_layout.addWidget(self.lock_bases, 0, 1)
        lock_layout.addWidget(self.lock_growths, 1, 0)
        lock_layout.addWidget(self.lock_ranks, 1, 1)
        lock_layout.addWidget(self.lock_items, 2, 0)
        lock_layout.addWidget(self.exclude_check, 3, 0, 1, 2)

        for cb in [self.lock_class, self.lock_bases, self.lock_growths,
                    self.lock_ranks, self.lock_items, self.exclude_check]:
            cb.stateChanged.connect(self._on_lock_changed)

        right_layout.addWidget(lock_group)

        # Current stats display
        stats_group = QGroupBox("Current Stats (from ROM)")
        stats_layout = QGridLayout(stats_group)

        self.stat_labels = {}
        stat_names = [
            ('Class ID', 'class_id'), ('Level', 'level'),
            ('HP', 'base_hp'), ('STR', 'base_str'), ('SKL', 'base_skl'),
            ('SPD', 'base_spd'), ('DEF', 'base_def'), ('RES', 'base_res'),
            ('LCK', 'base_lck'), ('CON', 'base_con'),
        ]
        for i, (display, key) in enumerate(stat_names):
            row, col = divmod(i, 2)
            label = QLabel(f"{display}:")
            label.setStyleSheet("color: #90a4ae; font-size: 11px;")
            val_label = QLabel("—")
            val_label.setStyleSheet("color: #e0e0e0; font-weight: bold; font-size: 11px;")
            stats_layout.addWidget(label, row, col * 2)
            stats_layout.addWidget(val_label, row, col * 2 + 1)
            self.stat_labels[key] = val_label

        right_layout.addWidget(stats_group)

        # Growth display
        growth_group = QGroupBox("Growths")
        growth_layout = QGridLayout(growth_group)
        self.growth_labels = {}
        growth_names = [
            ('HP%', 'growth_hp'), ('STR%', 'growth_str'), ('SKL%', 'growth_skl'),
            ('SPD%', 'growth_spd'), ('DEF%', 'growth_def'), ('RES%', 'growth_res'),
            ('LCK%', 'growth_lck'),
        ]
        for i, (display, key) in enumerate(growth_names):
            row, col = divmod(i, 2)
            label = QLabel(f"{display}:")
            label.setStyleSheet("color: #90a4ae; font-size: 11px;")
            val_label = QLabel("—")
            val_label.setStyleSheet("color: #e0e0e0; font-weight: bold; font-size: 11px;")
            growth_layout.addWidget(label, row, col * 2)
            growth_layout.addWidget(val_label, row, col * 2 + 1)
            self.growth_labels[key] = val_label

        right_layout.addWidget(growth_group)

        # Weapon ranks display
        rank_group = QGroupBox("Weapon Ranks")
        rank_layout = QGridLayout(rank_group)
        self.rank_labels = {}
        rank_names = [
            ('⚔ Sword', 'rank_sword'), ('🔱 Lance', 'rank_lance'),
            ('🪓 Axe', 'rank_axe'), ('🏹 Bow', 'rank_bow'),
            ('✨ Staff', 'rank_staff'), ('🔥 Anima', 'rank_anima'),
            ('☀ Light', 'rank_light'), ('🌑 Dark', 'rank_dark'),
        ]
        for i, (display, key) in enumerate(rank_names):
            row, col = divmod(i, 2)
            label = QLabel(f"{display}:")
            label.setStyleSheet("color: #90a4ae; font-size: 11px;")
            val_label = QLabel("—")
            val_label.setStyleSheet("color: #e0e0e0; font-weight: bold; font-size: 11px;")
            rank_layout.addWidget(label, row, col * 2)
            rank_layout.addWidget(val_label, row, col * 2 + 1)
            self.rank_labels[key] = val_label

        right_layout.addWidget(rank_group)
        right_layout.addStretch()

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([250, 500])
        layout.addWidget(splitter)

        self._current_char_id = None

    def on_rom_loaded(self):
        """Refresh character list after ROM is loaded."""
        self.char_list.clear()
        characters = self.state.get_character_list()

        for char in characters:
            item = QListWidgetItem()
            display = char['name']
            badges = []
            if char.get('is_lord'):
                badges.append("👑")
            if char.get('is_thief'):
                badges.append("🗝")
            if char.get('is_dancer'):
                badges.append("💃")
            if badges:
                display = f"{' '.join(badges)} {display}"

            item.setText(display)
            item.setData(Qt.UserRole, char['id'])

            # Load portrait icon
            portrait_path = self.state.get_portrait_path(char.get('portrait', ''))
            if portrait_path:
                pixmap = QPixmap(portrait_path)
                if not pixmap.isNull():
                    item.setIcon(QIcon(pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)))

            self.char_list.addItem(item)

    def _on_char_selected(self, row):
        if row < 0:
            return

        item = self.char_list.item(row)
        char_id = item.data(Qt.UserRole)
        self._current_char_id = char_id

        characters = self.state.get_character_list()
        char = None
        for c in characters:
            if c['id'] == char_id:
                char = c
                break

        if not char:
            return

        # Update header
        self.name_label.setText(char['name'])
        roles = []
        if char.get('is_lord'):
            roles.append("Lord")
        if char.get('is_required'):
            roles.append("Required")
        if char.get('is_thief'):
            roles.append("Thief")
        if char.get('is_dancer'):
            roles.append("Dancer/Bard")
        self.role_label.setText(" · ".join(roles) if roles else "Playable Character")

        # Portrait
        portrait_path = self.state.get_portrait_path(char.get('portrait', ''))
        if portrait_path:
            pixmap = QPixmap(portrait_path)
            if not pixmap.isNull():
                self.portrait_label.setPixmap(pixmap.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                self.portrait_label.setText("?")
        else:
            self.portrait_label.setText("?")

        # Update stat displays
        entry = char.get('entry', {})
        for key, label in self.stat_labels.items():
            val = entry.get(key, '—')
            label.setText(str(val))

        for key, label in self.growth_labels.items():
            val = entry.get(key, '—')
            label.setText(f"{val}%")

        for key, label in self.rank_labels.items():
            val = entry.get(key, 0)
            label.setText(self._rank_display(val))

        # Update lock checkboxes
        locks = self.state.settings.character_locks.get(char_id, {})
        self._updating_locks = True
        self.lock_class.setChecked(locks.get('class', False))
        self.lock_bases.setChecked(locks.get('bases', False))
        self.lock_growths.setChecked(locks.get('growths', False))
        self.lock_ranks.setChecked(locks.get('ranks', False))
        self.lock_items.setChecked(locks.get('items', False))
        self.exclude_check.setChecked(char_id in self.state.settings.excluded_character_ids)
        self._updating_locks = False

    def _on_lock_changed(self, _):
        if getattr(self, '_updating_locks', False):
            return
        if self._current_char_id is None:
            return

        cid = self._current_char_id
        self.state.settings.character_locks[cid] = {
            'class': self.lock_class.isChecked(),
            'bases': self.lock_bases.isChecked(),
            'growths': self.lock_growths.isChecked(),
            'ranks': self.lock_ranks.isChecked(),
            'items': self.lock_items.isChecked(),
        }

        excluded = set(self.state.settings.excluded_character_ids)
        if self.exclude_check.isChecked():
            excluded.add(cid)
        else:
            excluded.discard(cid)
        self.state.settings.excluded_character_ids = list(excluded)

    @staticmethod
    def _rank_display(value: int) -> str:
        if value == 0:
            return "—"
        elif value >= 251:
            return "S"
        elif value >= 181:
            return "A"
        elif value >= 121:
            return "B"
        elif value >= 71:
            return "C"
        elif value >= 31:
            return "D"
        else:
            return "E"

    def sync_to_settings(self):
        pass  # Locks are updated in real-time

    def sync_from_settings(self):
        if self._current_char_id is not None:
            # Re-trigger display of current character
            row = self.char_list.currentRow()
            if row >= 0:
                self._on_char_selected(row)