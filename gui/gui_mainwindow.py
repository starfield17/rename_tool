"""
gui_mainwindow.py - GUI Main Window

Contains two tabs:
1. Search and Replace Rename
2. Sequential Naming
"""

import sys
from pathlib import Path
from typing import Optional, List

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QTabWidget, QLabel, QLineEdit, QPushButton, QCheckBox, QComboBox,
    QSpinBox, QTableWidget, QTableWidgetItem, QTextEdit, QProgressBar,
    QFileDialog, QMessageBox, QHeaderView, QGroupBox, QSplitter,
    QStatusBar
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QColor

# 确保能导入模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import (
    FileItem, RenamePlan, RenameResult, RenameOptions, SortKey,
    list_suffixes
)
from .gui_workers import ScanWorker, PlanWorker, RenameWorker


class ReplaceTab(QWidget):
    """Search and Replace Rename Tab"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.files: List[FileItem] = []
        self.plan: Optional[RenamePlan] = None
        self.scan_worker: Optional[ScanWorker] = None
        self.plan_worker: Optional[PlanWorker] = None
        self.rename_worker: Optional[RenameWorker] = None

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Search settings group
        search_group = QGroupBox("Search Settings")
        search_layout = QGridLayout(search_group)

        # Directory selection
        search_layout.addWidget(QLabel("Directory:"), 0, 0)
        self.dir_edit = QLineEdit()
        self.dir_edit.setPlaceholderText("Select search directory...")
        search_layout.addWidget(self.dir_edit, 0, 1)
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self._browse_directory)
        search_layout.addWidget(self.browse_btn, 0, 2)

        # Search keyword
        search_layout.addWidget(QLabel("Keyword:"), 1, 0)
        self.keyword_edit = QLineEdit()
        self.keyword_edit.setPlaceholderText("Leave empty to match all files")
        search_layout.addWidget(self.keyword_edit, 1, 1, 1, 2)

        # Options
        options_layout = QHBoxLayout()
        self.case_check = QCheckBox("Case Sensitive")
        self.path_check = QCheckBox("Match Path")
        self.hidden_check = QCheckBox("Include Hidden Files")
        options_layout.addWidget(self.case_check)
        options_layout.addWidget(self.path_check)
        options_layout.addWidget(self.hidden_check)
        options_layout.addStretch()
        search_layout.addLayout(options_layout, 2, 0, 1, 3)

        # Search button
        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self._do_search)
        search_layout.addWidget(self.search_btn, 3, 0, 1, 3)

        layout.addWidget(search_group)

        # Replace settings group
        replace_group = QGroupBox("Replace Settings")
        replace_layout = QGridLayout(replace_group)

        replace_layout.addWidget(QLabel("Find:"), 0, 0)
        self.old_edit = QLineEdit()
        self.old_edit.setPlaceholderText("String to replace")
        replace_layout.addWidget(self.old_edit, 0, 1)

        replace_layout.addWidget(QLabel("Replace with:"), 1, 0)
        self.new_edit = QLineEdit()
        self.new_edit.setPlaceholderText("Replacement string (leave empty to delete)")
        replace_layout.addWidget(self.new_edit, 1, 1)

        # Preview button
        self.preview_btn = QPushButton("Preview")
        self.preview_btn.clicked.connect(self._do_preview)
        self.preview_btn.setEnabled(False)
        replace_layout.addWidget(self.preview_btn, 2, 0, 1, 2)

        layout.addWidget(replace_group)

        # Results table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Original Name", "New Name", "Status", "Path"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table, 1)

        # Progress and execution
        bottom_layout = QHBoxLayout()

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        bottom_layout.addWidget(self.progress_bar, 1)

        self.execute_btn = QPushButton("Execute Rename")
        self.execute_btn.clicked.connect(self._do_execute)
        self.execute_btn.setEnabled(False)
        self.execute_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px 16px; }")
        bottom_layout.addWidget(self.execute_btn)

        layout.addLayout(bottom_layout)

        # Status label
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)
    
    def _browse_directory(self):
        """Browse and select directory"""
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        if directory:
            self.dir_edit.setText(directory)

    def _do_search(self):
        """Execute search"""
        directory = self.dir_edit.text().strip()
        if not directory:
            QMessageBox.warning(self, "Warning", "Please select a directory first")
            return

        path = Path(directory)
        if not path.is_dir():
            QMessageBox.warning(self, "Warning", f"Directory does not exist: {directory}")
            return

        # Disable buttons
        self.search_btn.setEnabled(False)
        self.search_btn.setText("Searching...")
        self.preview_btn.setEnabled(False)
        self.execute_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress

        # Start scan thread
        self.scan_worker = ScanWorker(
            path,
            keyword=self.keyword_edit.text(),
            case_sensitive=self.case_check.isChecked(),
            match_path=self.path_check.isChecked(),
            include_hidden=self.hidden_check.isChecked(),
            recursive=True,
        )
        self.scan_worker.progress.connect(self._on_scan_progress)
        self.scan_worker.finished.connect(self._on_scan_finished)
        self.scan_worker.error.connect(self._on_scan_error)
        self.scan_worker.start()

    @Slot(str)
    def _on_scan_progress(self, msg: str):
        """Scan progress update"""
        self.status_label.setText(msg[-80:] if len(msg) > 80 else msg)

    @Slot(list)
    def _on_scan_finished(self, files: List[FileItem]):
        """Scan complete"""
        self.files = files
        self.search_btn.setEnabled(True)
        self.search_btn.setText("Search")
        self.progress_bar.setVisible(False)

        # Update table to display search results
        self._update_table_search_results()

        if files:
            self.preview_btn.setEnabled(True)
            self.status_label.setText(f"Found {len(files)} files")
        else:
            self.status_label.setText("No matching files found")

    @Slot(str)
    def _on_scan_error(self, error: str):
        """Scan error"""
        self.search_btn.setEnabled(True)
        self.search_btn.setText("Search")
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Error", f"Search failed: {error}")

    def _update_table_search_results(self):
        """Update table to display search results"""
        self.table.setRowCount(len(self.files))

        base_dir = Path(self.dir_edit.text())
        for i, f in enumerate(self.files):
            self.table.setItem(i, 0, QTableWidgetItem(f.name))
            self.table.setItem(i, 1, QTableWidgetItem(""))  # New filename pending preview
            self.table.setItem(i, 2, QTableWidgetItem(""))
            try:
                rel_path = str(f.path.parent.relative_to(base_dir))
            except ValueError:
                rel_path = str(f.path.parent)
            self.table.setItem(i, 3, QTableWidgetItem(rel_path))
    
    def _do_preview(self):
        """Generate preview"""
        old_str = self.old_edit.text()
        if not old_str:
            QMessageBox.warning(self, "Warning", "Please enter the string to replace")
            return

        self.preview_btn.setEnabled(False)
        self.preview_btn.setText("Generating...")

        # Start plan generation thread
        self.plan_worker = PlanWorker(
            self.files,
            mode="replace",
            old_str=old_str,
            new_str=self.new_edit.text(),
            case_sensitive=self.case_check.isChecked(),
        )
        self.plan_worker.finished.connect(self._on_plan_finished)
        self.plan_worker.error.connect(self._on_plan_error)
        self.plan_worker.start()

    @Slot(object)
    def _on_plan_finished(self, plan: RenamePlan):
        """Plan generation complete"""
        self.plan = plan
        self.preview_btn.setEnabled(True)
        self.preview_btn.setText("Preview")

        if plan.errors:
            QMessageBox.warning(self, "Warning", "\n".join(plan.errors))
            return

        # Update table to display preview results
        self._update_table_preview()

        if plan.valid_ops:
            self.execute_btn.setEnabled(True)
            self.status_label.setText(f"Will perform {plan.total_count} rename operations (conflict resolutions: {plan.conflict_count})")
        else:
            self.status_label.setText("No files need renaming")

    @Slot(str)
    def _on_plan_error(self, error: str):
        """Plan generation error"""
        self.preview_btn.setEnabled(True)
        self.preview_btn.setText("Preview")
        QMessageBox.critical(self, "Error", f"Failed to generate preview: {error}")

    def _update_table_preview(self):
        """Update table to display preview results"""
        if not self.plan:
            return

        # Create mapping: src -> op
        op_map = {str(op.src): op for op in self.plan.ops}

        base_dir = Path(self.dir_edit.text())
        for i, f in enumerate(self.files):
            op = op_map.get(str(f.path))
            if op:
                new_name_item = QTableWidgetItem(op.dst.name)
                if op.note:
                    # Conflict resolution
                    new_name_item.setBackground(QColor(255, 255, 200))
                    status_item = QTableWidgetItem("Conflict Resolved")
                    status_item.setForeground(QColor(200, 150, 0))
                elif op.is_same:
                    status_item = QTableWidgetItem("No Change")
                    status_item.setForeground(QColor(150, 150, 150))
                else:
                    status_item = QTableWidgetItem("Will Rename")
                    status_item.setForeground(QColor(0, 150, 0))

                self.table.setItem(i, 1, new_name_item)
                self.table.setItem(i, 2, status_item)
            else:
                self.table.setItem(i, 1, QTableWidgetItem(f.name))
                status_item = QTableWidgetItem("No Change")
                status_item.setForeground(QColor(150, 150, 150))
                self.table.setItem(i, 2, status_item)
    
    def _do_execute(self):
        """Execute rename"""
        if not self.plan or not self.plan.valid_ops:
            return

        # Confirm
        reply = QMessageBox.question(
            self, "Confirm",
            f"Are you sure you want to execute {self.plan.total_count} rename operations?\n\nThis action cannot be undone!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.execute_btn.setEnabled(False)
        self.execute_btn.setText("Executing...")
        self.preview_btn.setEnabled(False)
        self.search_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, self.plan.total_count * 2)

        # Start execution thread
        self.rename_worker = RenameWorker(self.plan, dry_run=False)
        self.rename_worker.progress.connect(self._on_rename_progress)
        self.rename_worker.finished.connect(self._on_rename_finished)
        self.rename_worker.error.connect(self._on_rename_error)
        self.rename_worker.start()

    @Slot(int, int, str)
    def _on_rename_progress(self, current: int, total: int, msg: str):
        """Execution progress update"""
        self.progress_bar.setValue(current)
        self.status_label.setText(msg)

    @Slot(object)
    def _on_rename_finished(self, result: RenameResult):
        """Execution complete"""
        self.execute_btn.setEnabled(False)
        self.execute_btn.setText("Execute Rename")
        self.preview_btn.setEnabled(False)
        self.search_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

        # Display results
        msg = f"Rename complete!\n\nSuccess: {result.success_count}\nFailed: {result.failed_count}"
        if result.failed_count > 0:
            msg += "\n\nFailure Details:\n"
            for op, error in result.failed[:5]:
                msg += f"  {op.src.name}: {error}\n"
            if len(result.failed) > 5:
                msg += f"  ... and {len(result.failed) - 5} more failures"

        QMessageBox.information(self, "Complete", msg)

        # Clear state
        self.files = []
        self.plan = None
        self.table.setRowCount(0)
        self.status_label.setText("Complete")

    @Slot(str)
    def _on_rename_error(self, error: str):
        """Execution error"""
        self.execute_btn.setEnabled(True)
        self.execute_btn.setText("Execute Rename")
        self.preview_btn.setEnabled(True)
        self.search_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Error", f"Execution failed: {error}")


class SequenceTab(QWidget):
    """Sequential Naming Tab"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.files: List[FileItem] = []
        self.plan: Optional[RenamePlan] = None
        self.scan_worker: Optional[ScanWorker] = None
        self.plan_worker: Optional[PlanWorker] = None
        self.rename_worker: Optional[RenameWorker] = None

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Directory settings group
        dir_group = QGroupBox("Directory Settings")
        dir_layout = QGridLayout(dir_group)

        dir_layout.addWidget(QLabel("Directory:"), 0, 0)
        self.dir_edit = QLineEdit()
        self.dir_edit.setPlaceholderText("Select target directory (non-recursive)...")
        dir_layout.addWidget(self.dir_edit, 0, 1)
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self._browse_directory)
        dir_layout.addWidget(self.browse_btn, 0, 2)

        dir_layout.addWidget(QLabel("Suffix Filter:"), 1, 0)
        self.suffix_combo = QComboBox()
        self.suffix_combo.setEditable(True)
        self.suffix_combo.addItem("(All)")
        dir_layout.addWidget(self.suffix_combo, 1, 1, 1, 2)

        self.scan_btn = QPushButton("Scan")
        self.scan_btn.clicked.connect(self._do_scan)
        dir_layout.addWidget(self.scan_btn, 2, 0, 1, 3)

        layout.addWidget(dir_group)

        # Naming settings group
        name_group = QGroupBox("Naming Settings")
        name_layout = QGridLayout(name_group)

        name_layout.addWidget(QLabel("Sort By:"), 0, 0)
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Modification Time (mtime)", "File Size (size)", "Filename (name)", "Creation Time (ctime)"])
        name_layout.addWidget(self.sort_combo, 0, 1)

        self.reverse_check = QCheckBox("Reverse Sort")
        name_layout.addWidget(self.reverse_check, 0, 2)

        name_layout.addWidget(QLabel("Start Number:"), 1, 0)
        self.start_spin = QSpinBox()
        self.start_spin.setRange(0, 99999)
        self.start_spin.setValue(1)
        name_layout.addWidget(self.start_spin, 1, 1)

        name_layout.addWidget(QLabel("Padding Digits:"), 2, 0)
        self.padding_spin = QSpinBox()
        self.padding_spin.setRange(0, 10)
        self.padding_spin.setValue(0)
        self.padding_spin.setSpecialValueText("No Padding")
        name_layout.addWidget(self.padding_spin, 2, 1)

        name_layout.addWidget(QLabel("Prefix:"), 3, 0)
        self.prefix_edit = QLineEdit()
        self.prefix_edit.setPlaceholderText("e.g., img_")
        name_layout.addWidget(self.prefix_edit, 3, 1, 1, 2)

        self.preview_btn = QPushButton("Preview")
        self.preview_btn.clicked.connect(self._do_preview)
        self.preview_btn.setEnabled(False)
        name_layout.addWidget(self.preview_btn, 4, 0, 1, 3)

        layout.addWidget(name_group)

        # Results table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Original Name", "New Name", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table, 1)

        # Progress and execution
        bottom_layout = QHBoxLayout()

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        bottom_layout.addWidget(self.progress_bar, 1)

        self.execute_btn = QPushButton("Execute Rename")
        self.execute_btn.clicked.connect(self._do_execute)
        self.execute_btn.setEnabled(False)
        self.execute_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px 16px; }")
        bottom_layout.addWidget(self.execute_btn)

        layout.addLayout(bottom_layout)

        # Status label
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)
    
    def _browse_directory(self):
        """Browse and select directory"""
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        if directory:
            self.dir_edit.setText(directory)
            # Update suffix list
            self._update_suffix_list(directory)

    def _update_suffix_list(self, directory: str):
        """Update suffix dropdown list"""
        suffixes = list_suffixes(Path(directory))
        self.suffix_combo.clear()
        self.suffix_combo.addItem("(All)")
        for suffix in suffixes:
            self.suffix_combo.addItem(suffix)

    def _do_scan(self):
        """Execute scan"""
        directory = self.dir_edit.text().strip()
        if not directory:
            QMessageBox.warning(self, "Warning", "Please select a directory first")
            return

        path = Path(directory)
        if not path.is_dir():
            QMessageBox.warning(self, "Warning", f"Directory does not exist: {directory}")
            return

        suffix_filter = self.suffix_combo.currentText()
        if suffix_filter == "(All)":
            suffix_filter = None

        self.scan_btn.setEnabled(False)
        self.scan_btn.setText("Scanning...")
        self.preview_btn.setEnabled(False)
        self.execute_btn.setEnabled(False)

        # Start scan thread
        self.scan_worker = ScanWorker(
            path,
            recursive=False,
            suffix_filter=suffix_filter,
        )
        self.scan_worker.finished.connect(self._on_scan_finished)
        self.scan_worker.error.connect(self._on_scan_error)
        self.scan_worker.start()

    @Slot(list)
    def _on_scan_finished(self, files: List[FileItem]):
        """Scan complete"""
        self.files = files
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("Scan")

        # Update table
        self.table.setRowCount(len(files))
        for i, f in enumerate(files):
            self.table.setItem(i, 0, QTableWidgetItem(f.name))
            self.table.setItem(i, 1, QTableWidgetItem(""))
            self.table.setItem(i, 2, QTableWidgetItem(""))

        if files:
            self.preview_btn.setEnabled(True)
            self.status_label.setText(f"Found {len(files)} files")
        else:
            self.status_label.setText("No files found")

    @Slot(str)
    def _on_scan_error(self, error: str):
        """Scan error"""
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("Scan")
        QMessageBox.critical(self, "Error", f"Scan failed: {error}")
    
    def _do_preview(self):
        """Generate preview"""
        if not self.files:
            return

        sort_map = {
            0: SortKey.MTIME,
            1: SortKey.SIZE,
            2: SortKey.NAME,
            3: SortKey.CTIME,
        }
        sort_key = sort_map.get(self.sort_combo.currentIndex(), SortKey.MTIME)

        self.preview_btn.setEnabled(False)
        self.preview_btn.setText("Generating...")

        self.plan_worker = PlanWorker(
            self.files,
            mode="sequence",
            sort_by=sort_key,
            reverse=self.reverse_check.isChecked(),
            seq_start=self.start_spin.value(),
            padding=self.padding_spin.value(),
            prefix=self.prefix_edit.text(),
        )
        self.plan_worker.finished.connect(self._on_plan_finished)
        self.plan_worker.error.connect(self._on_plan_error)
        self.plan_worker.start()

    @Slot(object)
    def _on_plan_finished(self, plan: RenamePlan):
        """Plan generation complete"""
        self.plan = plan
        self.preview_btn.setEnabled(True)
        self.preview_btn.setText("Preview")

        if plan.errors:
            QMessageBox.warning(self, "Warning", "\n".join(plan.errors))
            return

        # Update table
        op_map = {str(op.src): op for op in plan.ops}
        for i, f in enumerate(self.files):
            op = op_map.get(str(f.path))
            if op:
                self.table.setItem(i, 1, QTableWidgetItem(op.dst.name))
                if op.note:
                    status = QTableWidgetItem("Conflict Resolved")
                    status.setForeground(QColor(200, 150, 0))
                elif op.is_same:
                    status = QTableWidgetItem("No Change")
                    status.setForeground(QColor(150, 150, 150))
                else:
                    status = QTableWidgetItem("Will Rename")
                    status.setForeground(QColor(0, 150, 0))
                self.table.setItem(i, 2, status)

        if plan.valid_ops:
            self.execute_btn.setEnabled(True)
            self.status_label.setText(f"Will perform {plan.total_count} rename operations (conflict resolutions: {plan.conflict_count})")
        else:
            self.status_label.setText("No files need renaming")

    @Slot(str)
    def _on_plan_error(self, error: str):
        """Plan generation error"""
        self.preview_btn.setEnabled(True)
        self.preview_btn.setText("Preview")
        QMessageBox.critical(self, "Error", f"Failed to generate preview: {error}")
    
    def _do_execute(self):
        """Execute rename"""
        if not self.plan or not self.plan.valid_ops:
            return

        reply = QMessageBox.question(
            self, "Confirm",
            f"Are you sure you want to execute {self.plan.total_count} rename operations?\n\nThis action cannot be undone!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.execute_btn.setEnabled(False)
        self.execute_btn.setText("Executing...")
        self.preview_btn.setEnabled(False)
        self.scan_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, self.plan.total_count * 2)

        self.rename_worker = RenameWorker(self.plan, dry_run=False)
        self.rename_worker.progress.connect(self._on_rename_progress)
        self.rename_worker.finished.connect(self._on_rename_finished)
        self.rename_worker.error.connect(self._on_rename_error)
        self.rename_worker.start()

    @Slot(int, int, str)
    def _on_rename_progress(self, current: int, total: int, msg: str):
        self.progress_bar.setValue(current)
        self.status_label.setText(msg)

    @Slot(object)
    def _on_rename_finished(self, result: RenameResult):
        self.execute_btn.setEnabled(False)
        self.execute_btn.setText("Execute Rename")
        self.preview_btn.setEnabled(False)
        self.scan_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

        msg = f"Rename complete!\n\nSuccess: {result.success_count}\nFailed: {result.failed_count}"
        QMessageBox.information(self, "Complete", msg)

        self.files = []
        self.plan = None
        self.table.setRowCount(0)
        self.status_label.setText("Complete")

    @Slot(str)
    def _on_rename_error(self, error: str):
        self.execute_btn.setEnabled(True)
        self.execute_btn.setText("Execute Rename")
        self.preview_btn.setEnabled(True)
        self.scan_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Error", f"Execution failed: {error}")


class MainWindow(QMainWindow):
    """Main window"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Batch Rename Tool")
        self.setMinimumSize(800, 600)

        # Create central widget
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)

        # Create tabs
        self.tabs = QTabWidget()
        self.replace_tab = ReplaceTab()
        self.sequence_tab = SequenceTab()

        self.tabs.addTab(self.replace_tab, "Search and Replace")
        self.tabs.addTab(self.sequence_tab, "Sequential Naming")

        layout.addWidget(self.tabs)

        # Status bar
        self.statusBar().showMessage("Ready")
