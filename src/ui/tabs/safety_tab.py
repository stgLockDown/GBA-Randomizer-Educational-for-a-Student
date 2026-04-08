"""
Safety Tab: persistent issues panel with errors, warnings, and auto-fix controls.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QTreeWidget, QTreeWidgetItem, QPushButton, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush


class SafetyTab(QWidget):
    def __init__(self, app_state, parent=None):
        super().__init__(parent)
        self.state = app_state
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Summary bar
        self.summary_frame = QFrame()
        self.summary_frame.setStyleSheet("""
            QFrame {
                background: #1a1a2e;
                border: 1px solid #303050;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        summary_layout = QHBoxLayout(self.summary_frame)

        self.error_count_label = QLabel("❌ 0 Errors")
        self.error_count_label.setStyleSheet("color: #ef5350; font-weight: bold; font-size: 14px;")
        self.warning_count_label = QLabel("⚠ 0 Warnings")
        self.warning_count_label.setStyleSheet("color: #ffb74d; font-weight: bold; font-size: 14px;")
        self.fixed_count_label = QLabel("✅ 0 Auto-fixed")
        self.fixed_count_label.setStyleSheet("color: #66bb6a; font-weight: bold; font-size: 14px;")

        summary_layout.addWidget(self.error_count_label)
        summary_layout.addWidget(self.warning_count_label)
        summary_layout.addWidget(self.fixed_count_label)
        summary_layout.addStretch()

        self.build_status_label = QLabel("ℹ Load a ROM and run Preview to see validation results.")
        self.build_status_label.setStyleSheet("color: #78909c; font-size: 12px;")
        summary_layout.addWidget(self.build_status_label)

        layout.addWidget(self.summary_frame)

        # Issues tree
        issues_group = QGroupBox("Issues")
        issues_layout = QVBoxLayout(issues_group)

        self.issues_tree = QTreeWidget()
        self.issues_tree.setHeaderLabels(["Severity", "Character", "Category", "Message", "Suggestion", "Status"])
        self.issues_tree.setColumnWidth(0, 70)
        self.issues_tree.setColumnWidth(1, 100)
        self.issues_tree.setColumnWidth(2, 80)
        self.issues_tree.setColumnWidth(3, 300)
        self.issues_tree.setColumnWidth(4, 200)
        self.issues_tree.setColumnWidth(5, 80)
        self.issues_tree.setAlternatingRowColors(True)
        self.issues_tree.setRootIsDecorated(False)
        self.issues_tree.setStyleSheet("""
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
            }
        """)
        issues_layout.addWidget(self.issues_tree)

        layout.addWidget(issues_group, 1)

        # Engine warnings
        self.engine_warnings_group = QGroupBox("Engine Warnings")
        ew_layout = QVBoxLayout(self.engine_warnings_group)
        self.engine_warnings_label = QLabel("No engine warnings.")
        self.engine_warnings_label.setStyleSheet("color: #78909c; font-size: 11px;")
        self.engine_warnings_label.setWordWrap(True)
        ew_layout.addWidget(self.engine_warnings_label)
        self.engine_warnings_group.setVisible(False)
        layout.addWidget(self.engine_warnings_group)

    def clear_issues(self):
        """Clear all displayed issues."""
        self.issues_tree.clear()
        self.error_count_label.setText("❌ 0 Errors")
        self.warning_count_label.setText("⚠ 0 Warnings")
        self.fixed_count_label.setText("✅ 0 Auto-fixed")
        self.build_status_label.setText("ℹ Run Preview to see validation results.")
        self.engine_warnings_group.setVisible(False)

    def refresh(self):
        """Refresh the issues display from app state."""
        self.issues_tree.clear()

        issues = self.state.validation_issues
        errors = [i for i in issues if i.severity == 'error' and not i.fixed]
        warnings = [i for i in issues if i.severity == 'warning' and not i.fixed]
        fixed = [i for i in issues if i.fixed]

        self.error_count_label.setText(f"❌ {len(errors)} Error{'s' if len(errors) != 1 else ''}")
        self.warning_count_label.setText(f"⚠ {len(warnings)} Warning{'s' if len(warnings) != 1 else ''}")
        self.fixed_count_label.setText(f"✅ {len(fixed)} Auto-fixed")

        if errors:
            self.build_status_label.setText("🚫 Build blocked — errors must be resolved.")
            self.build_status_label.setStyleSheet("color: #ef5350; font-size: 12px; font-weight: bold;")
        elif warnings:
            self.build_status_label.setText("⚠ Build allowed with warnings.")
            self.build_status_label.setStyleSheet("color: #ffb74d; font-size: 12px;")
        else:
            self.build_status_label.setText("✅ All checks passed.")
            self.build_status_label.setStyleSheet("color: #66bb6a; font-size: 12px;")

        # Populate tree
        error_brush = QBrush(QColor("#ef5350"))
        warning_brush = QBrush(QColor("#ffb74d"))
        fixed_brush = QBrush(QColor("#66bb6a"))

        for issue in issues:
            item = QTreeWidgetItem()

            if issue.fixed:
                item.setText(0, "FIXED")
                item.setForeground(0, fixed_brush)
            elif issue.severity == 'error':
                item.setText(0, "ERROR")
                item.setForeground(0, error_brush)
            else:
                item.setText(0, "WARN")
                item.setForeground(0, warning_brush)

            item.setText(1, issue.character_name)
            item.setText(2, issue.category.title())
            item.setText(3, issue.message)
            item.setText(4, issue.suggestion)
            item.setText(5, "✅ Fixed" if issue.fixed else ("🔧 Fixable" if issue.auto_fixable else "Manual"))

            self.issues_tree.addTopLevelItem(item)

        # Engine warnings
        engine_warnings = self.state.preview_warnings
        if engine_warnings:
            self.engine_warnings_group.setVisible(True)
            self.engine_warnings_label.setText("\n".join(f"⚠ {w}" for w in engine_warnings))
        else:
            self.engine_warnings_group.setVisible(False)