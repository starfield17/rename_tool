"""
models_fs.py - Core Data Structure Definitions

Contains:
- FileItem: File information
- RenameOp: Single rename operation
- RenamePlan: Batch rename plan
- RenameOptions: Rename options configuration
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Callable
from enum import Enum
import platform
import os


class SortKey(Enum):
    """Sort key enumeration"""
    MTIME = "mtime"      # Modification time
    SIZE = "size"        # File size
    NAME = "name"        # Filename
    CTIME = "ctime"      # Creation time (varies across platforms)


class ConflictPolicy(Enum):
    """Conflict handling policy"""
    SUFFIX_NUMBER = "suffix_number"  # Add _1, _2, _3...
    SKIP = "skip"                    # Skip
    OVERWRITE = "overwrite"          # Overwrite (dangerous)


@dataclass
class FileItem:
    """File information data class"""
    path: Path                      # Full path
    name: str                       # Filename (with suffix)
    stem: str                       # Filename (without suffix)
    suffix: str                     # Suffix (e.g., .png)
    size: int                       # File size (bytes)
    mtime: float                    # Modification time (timestamp)
    ctime: float                    # Creation/change time (timestamp)

    @classmethod
    def from_path(cls, p: Path) -> "FileItem":
        """Create FileItem from Path object"""
        stat = p.stat()
        return cls(
            path=p,
            name=p.name,
            stem=p.stem,
            suffix=p.suffix,
            size=stat.st_size,
            mtime=stat.st_mtime,
            ctime=stat.st_ctime,
        )

    def relative_to(self, base: Path) -> str:
        """Get relative path string"""
        try:
            return str(self.path.relative_to(base))
        except ValueError:
            return str(self.path)


@dataclass
class RenameOp:
    """Single rename operation"""
    src: Path                       # Source path
    dst: Path                       # Destination path
    note: str = ""                  # Note (e.g., conflict resolution explanation)

    @property
    def is_same(self) -> bool:
        """Whether source and destination are the same"""
        return self.src == self.dst

    @property
    def is_case_only_change(self) -> bool:
        """Whether it's only a case change"""
        return (self.src.parent == self.dst.parent and
                self.src.name.lower() == self.dst.name.lower() and
                self.src.name != self.dst.name)


@dataclass
class RenameOptions:
    """Rename options configuration"""
    # Conflict handling
    conflict_policy: ConflictPolicy = ConflictPolicy.SUFFIX_NUMBER

    # Case-sensitive detection (Windows/macOS default to insensitive)
    case_insensitive_detect: bool = field(default_factory=lambda: platform.system() in ("Windows", "Darwin"))

    # Search options
    match_path: bool = False        # Whether to match relative path (not just filename)
    include_hidden: bool = False    # Whether to include hidden files
    ignore_dirs: List[str] = field(default_factory=lambda: [".git", "__pycache__", ".rename_backup", "node_modules"])

    # Sequential naming options
    seq_start: int = 1              # Starting number
    seq_padding: int = 0            # Zero padding digits (0 means no padding)
    seq_prefix: str = ""            # Prefix
    seq_suffix_str: str = ""        # Suffix (note: not file extension)

    # Execution options
    dry_run: bool = False           # Preview only, do not actually execute
    backup_log: bool = True         # Whether to save execution logs


@dataclass
class RenamePlan:
    """Batch rename plan"""
    ops: List[RenameOp] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    options: RenameOptions = field(default_factory=RenameOptions)

    @property
    def valid_ops(self) -> List[RenameOp]:
        """Get valid operations (excluding source=destination)"""
        return [op for op in self.ops if not op.is_same]

    @property
    def conflict_count(self) -> int:
        """Number of conflict resolutions"""
        return sum(1 for op in self.ops if op.note.startswith("conflict resolved"))

    @property
    def total_count(self) -> int:
        """Total number of operations"""
        return len(self.valid_ops)

    def add_op(self, src: Path, dst: Path, note: str = "") -> None:
        """Add operation"""
        self.ops.append(RenameOp(src=src, dst=dst, note=note))

    def add_warning(self, msg: str) -> None:
        """Add warning"""
        self.warnings.append(msg)

    def add_error(self, msg: str) -> None:
        """Add error"""
        self.errors.append(msg)

    def summary(self) -> str:
        """Generate summary"""
        lines = [
            f"Rename Plan Summary:",
            f"  - Total operations: {self.total_count}",
            f"  - Conflict resolutions: {self.conflict_count}",
            f"  - Warnings: {len(self.warnings)}",
            f"  - Errors: {len(self.errors)}",
        ]
        return "\n".join(lines)


def is_case_insensitive_fs() -> bool:
    """Detect if current filesystem is case-insensitive"""
    return platform.system() in ("Windows", "Darwin")


def normalize_for_comparison(name: str, case_insensitive: bool) -> str:
    """Normalize filename for comparison"""
    if case_insensitive:
        return name.casefold()
    return name
