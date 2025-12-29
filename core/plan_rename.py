"""
plan_rename.py - Rename Plan Generation Module

Responsibilities:
- Generate preliminary target names (replace/sequential naming)
- Conflict detection and resolution (auto add _1, _2...)
- Output RenamePlan
"""

from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple
from collections import defaultdict

from .models_fs import (
    FileItem, RenameOp, RenamePlan, RenameOptions, 
    SortKey, ConflictPolicy, normalize_for_comparison
)
from .text_match import replace_text, is_valid_filename
from .sort_rules import sort_files, sort_by_path
from .scan_files import get_existing_names


class ConflictResolver:
    """Conflict resolver"""

    def __init__(self, case_insensitive: bool = True):
        """
        Initialize conflict resolver

        Args:
            case_insensitive: Whether case-insensitive
        """
        self.case_insensitive = case_insensitive
        # Occupied names grouped by directory
        # key: directory path, value: occupied names set (normalized)
        self.occupied: Dict[Path, Set[str]] = defaultdict(set)

    def _normalize(self, name: str) -> str:
        """Normalize filename for comparison"""
        return normalize_for_comparison(name, self.case_insensitive)

    def add_existing(self, directory: Path, names: Set[str]) -> None:
        """
        Add existing filenames (on disk)

        Args:
            directory: Directory
            names: Filename set
        """
        normalized = {self._normalize(n) for n in names}
        self.occupied[directory].update(normalized)

    def remove_participating(self, directory: Path, names: Set[str]) -> None:
        """
        Remove participating source filenames (these names will be freed)

        Args:
            directory: Directory
            names: Filename set to remove
        """
        normalized = {self._normalize(n) for n in names}
        self.occupied[directory] -= normalized

    def is_occupied(self, directory: Path, name: str) -> bool:
        """Check if name is already occupied"""
        return self._normalize(name) in self.occupied[directory]

    def mark_occupied(self, directory: Path, name: str) -> None:
        """Mark name as occupied"""
        self.occupied[directory].add(self._normalize(name))

    def resolve(self, directory: Path, desired_name: str) -> Tuple[str, bool]:
        """
        Resolve conflict, return available filename

        Args:
            directory: Directory
            desired_name: Desired filename

        Returns:
            (actual filename, whether conflict occurred)
        """
        if not self.is_occupied(directory, desired_name):
            self.mark_occupied(directory, desired_name)
            return desired_name, False

        # Conflict occurred, try adding _1, _2, _3...
        stem = Path(desired_name).stem
        suffix = Path(desired_name).suffix

        n = 1
        while True:
            candidate = f"{stem}_{n}{suffix}"
            if not self.is_occupied(directory, candidate):
                self.mark_occupied(directory, candidate)
                return candidate, True
            n += 1
            # Safety limit
            if n > 10000:
                raise RuntimeError(f"Cannot find available name for {desired_name} (tried over 10000 times)")


def plan_replace_rename(
    files: List[FileItem],
    old_str: str,
    new_str: str,
    case_sensitive: bool = True,
    options: Optional[RenameOptions] = None
) -> RenamePlan:
    """
    Generate string replacement rename plan

    Args:
        files: File list
        old_str: String to replace
        new_str: Replacement string
        case_sensitive: Whether case-sensitive
        options: Rename options

    Returns:
        Rename plan
    """
    if options is None:
        options = RenameOptions()

    plan = RenamePlan(options=options)

    if not old_str:
        plan.add_error("Replacement string cannot be empty")
        return plan

    # Group by directory
    files_by_dir: Dict[Path, List[FileItem]] = defaultdict(list)
    for f in files:
        files_by_dir[f.path.parent].append(f)

    # Process each directory
    for directory, dir_files in files_by_dir.items():
        # Sort by path to ensure stable processing order
        dir_files = sort_by_path(dir_files)

        # Create conflict resolver
        resolver = ConflictResolver(case_insensitive=options.case_insensitive_detect)

        # Add existing filenames in the directory
        existing = get_existing_names(directory, options.case_insensitive_detect)
        resolver.add_existing(directory, existing)

        # Remove participating source filenames (these names will be freed)
        participating_names = {f.name for f in dir_files}
        resolver.remove_participating(directory, participating_names)

        # Generate rename plan
        for f in dir_files:
            # Replace filename
            new_name = replace_text(f.name, old_str, new_str, case_sensitive)

            # Skip if name hasn't changed
            if new_name == f.name:
                continue

            # Validate new filename
            valid, error = is_valid_filename(new_name)
            if not valid:
                plan.add_warning(f"Skip {f.path}: {error}")
                continue

            # Resolve conflict
            final_name, had_conflict = resolver.resolve(directory, new_name)

            dst = directory / final_name
            note = ""
            if had_conflict:
                note = f"conflict resolved: {new_name} -> {final_name}"

            plan.add_op(f.path, dst, note)

    return plan


def plan_sequence_rename(
    files: List[FileItem],
    sort_by: SortKey = SortKey.MTIME,
    reverse: bool = False,
    start: int = 1,
    padding: int = 0,
    prefix: str = "",
    suffix_str: str = "",
    options: Optional[RenameOptions] = None
) -> RenamePlan:
    """
    Generate sequential naming rename plan

    Args:
        files: File list
        sort_by: Sorting method
        reverse: Whether to sort in reverse
        start: Starting number
        padding: Zero padding digits
        prefix: Prefix
        suffix_str: Suffix (string before file extension)
        options: Rename options

    Returns:
        Rename plan
    """
    if options is None:
        options = RenameOptions()

    plan = RenamePlan(options=options)

    if not files:
        return plan

    # All files must be in the same directory
    directories = {f.path.parent for f in files}
    if len(directories) > 1:
        plan.add_error("Sequential naming can only be done in the same directory")
        return plan

    directory = directories.pop()

    # Sort
    sorted_files = sort_files(files, sort_by, reverse)

    # Create conflict resolver
    resolver = ConflictResolver(case_insensitive=options.case_insensitive_detect)

    # Add existing filenames in the directory
    existing = get_existing_names(directory, options.case_insensitive_detect)
    resolver.add_existing(directory, existing)

    # Remove participating source filenames
    participating_names = {f.name for f in files}
    resolver.remove_participating(directory, participating_names)

    # Generate rename plan
    for i, f in enumerate(sorted_files):
        num = start + i

        # Generate number string
        if padding > 0:
            num_str = str(num).zfill(padding)
        else:
            num_str = str(num)

        # Generate new filename
        new_name = f"{prefix}{num_str}{suffix_str}{f.suffix}"

        # Validate new filename
        valid, error = is_valid_filename(new_name)
        if not valid:
            plan.add_warning(f"Skip {f.path}: {error}")
            continue

        # Resolve conflict
        final_name, had_conflict = resolver.resolve(directory, new_name)

        dst = directory / final_name
        note = ""
        if had_conflict:
            note = f"conflict resolved: {new_name} -> {final_name}"

        plan.add_op(f.path, dst, note)

    return plan


def validate_plan(plan: RenamePlan) -> List[str]:
    """
    Validate rename plan

    Args:
        plan: Rename plan

    Returns:
        Error list
    """
    errors = []

    # Check if source files exist
    for op in plan.ops:
        if not op.src.exists():
            errors.append(f"Source file does not exist: {op.src}")

    # Check for duplicate destinations
    dst_set: Dict[str, List[Path]] = defaultdict(list)
    for op in plan.ops:
        key = str(op.dst).lower() if plan.options.case_insensitive_detect else str(op.dst)
        dst_set[key].append(op.src)

    for dst_key, srcs in dst_set.items():
        if len(srcs) > 1:
            errors.append(f"Multiple files have the same destination: {srcs} -> {dst_key}")

    return errors
