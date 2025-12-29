"""
gui_workers.py - GUI Worker Threads

Provides background execution of long tasks to avoid blocking UI
"""

import sys
from pathlib import Path
from typing import Optional, List

from PySide6.QtCore import QThread, Signal, QObject

# 确保能导入 core 模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import (
    scan_recursive, scan_directory,
    plan_replace_rename, plan_sequence_rename, execute_rename,
    RenameOptions, SortKey, FileItem, RenamePlan, RenameResult
)


class ScanWorker(QThread):
    """File scanning worker thread"""

    # Signals
    progress = Signal(str)          # Progress message
    finished = Signal(list)         # Complete, returns file list
    error = Signal(str)             # Error message

    def __init__(
        self,
        directory: Path,
        keyword: str = "",
        case_sensitive: bool = True,
        match_path: bool = False,
        include_hidden: bool = False,
        recursive: bool = True,
        suffix_filter: Optional[str] = None,
        parent: Optional[QObject] = None
    ):
        super().__init__(parent)
        self.directory = directory
        self.keyword = keyword
        self.case_sensitive = case_sensitive
        self.match_path = match_path
        self.include_hidden = include_hidden
        self.recursive = recursive
        self.suffix_filter = suffix_filter
        self._cancelled = False

    def cancel(self):
        """Cancel scan"""
        self._cancelled = True

    def run(self):
        try:
            def progress_callback(msg: str):
                if self._cancelled:
                    raise InterruptedError("Scan cancelled")
                self.progress.emit(msg)

            if self.recursive:
                files = scan_recursive(
                    self.directory,
                    keyword=self.keyword,
                    case_sensitive=self.case_sensitive,
                    match_path=self.match_path,
                    include_hidden=self.include_hidden,
                    progress_callback=progress_callback,
                )
            else:
                files = scan_directory(
                    self.directory,
                    suffix_filter=self.suffix_filter,
                    include_hidden=self.include_hidden,
                )

            if not self._cancelled:
                self.finished.emit(files)
        except InterruptedError:
            self.finished.emit([])
        except Exception as e:
            self.error.emit(str(e))


class RenameWorker(QThread):
    """Rename execution worker thread"""

    # Signals
    progress = Signal(int, int, str)    # current, total, message
    finished = Signal(object)           # RenameResult
    error = Signal(str)                 # Error message

    def __init__(
        self,
        plan: RenamePlan,
        dry_run: bool = False,
        parent: Optional[QObject] = None
    ):
        super().__init__(parent)
        self.plan = plan
        self.dry_run = dry_run

    def run(self):
        try:
            def progress_callback(current: int, total: int, msg: str):
                self.progress.emit(current, total, msg)

            result = execute_rename(
                self.plan,
                dry_run=self.dry_run,
                progress_callback=progress_callback,
            )

            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class PlanWorker(QThread):
    """Rename plan generation worker thread"""

    # Signals
    progress = Signal(str)              # Progress message
    finished = Signal(object)           # RenamePlan
    error = Signal(str)                 # Error message

    def __init__(
        self,
        files: List[FileItem],
        mode: str,  # "replace" or "sequence"
        # replace mode parameters
        old_str: str = "",
        new_str: str = "",
        case_sensitive: bool = True,
        # sequence mode parameters
        sort_by: SortKey = SortKey.MTIME,
        reverse: bool = False,
        seq_start: int = 1,
        padding: int = 0,
        prefix: str = "",
        # common options
        options: Optional[RenameOptions] = None,
        parent: Optional[QObject] = None
    ):
        super().__init__(parent)
        self.files = files
        self.mode = mode
        self.old_str = old_str
        self.new_str = new_str
        self.case_sensitive = case_sensitive
        self.sort_by = sort_by
        self.reverse = reverse
        self.seq_start = seq_start
        self.padding = padding
        self.prefix = prefix
        self.options = options or RenameOptions()

    def run(self):
        try:
            self.progress.emit("Generating rename plan...")

            if self.mode == "replace":
                plan = plan_replace_rename(
                    self.files,
                    old_str=self.old_str,
                    new_str=self.new_str,
                    case_sensitive=self.case_sensitive,
                    options=self.options,
                )
            elif self.mode == "sequence":
                plan = plan_sequence_rename(
                    self.files,
                    sort_by=self.sort_by,
                    reverse=self.reverse,
                    start=self.seq_start,
                    padding=self.padding,
                    prefix=self.prefix,
                    options=self.options,
                )
            else:
                raise ValueError(f"Unknown mode: {self.mode}")

            self.finished.emit(plan)
        except Exception as e:
            self.error.emit(str(e))
