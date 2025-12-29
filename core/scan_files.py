"""
scan_files.py - File Scanning Module

Provides recursive and non-recursive file scanning functionality
"""

from pathlib import Path
from typing import List, Optional, Callable, Generator
import os

from .models_fs import FileItem, RenameOptions
from .text_match import contains


def scan_recursive(
    root: Path,
    keyword: str = "",
    case_sensitive: bool = True,
    match_path: bool = False,
    include_hidden: bool = False,
    ignore_dirs: Optional[List[str]] = None,
    file_filter: Optional[Callable[[Path], bool]] = None,
    progress_callback: Optional[Callable[[str], None]] = None
) -> List[FileItem]:
    """
    Recursively scan folder for files containing keyword

    Args:
        root: Root directory
        keyword: Search keyword (empty string means match all)
        case_sensitive: Whether case-sensitive
        match_path: Whether to match relative path (not just filename)
        include_hidden: Whether to include hidden files
        ignore_dirs: List of directories to ignore
        file_filter: Additional file filter function
        progress_callback: Progress callback function

    Returns:
        List of matched files
    """
    if ignore_dirs is None:
        ignore_dirs = [".git", "__pycache__", ".rename_backup", "node_modules"]

    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError(f"Directory does not exist: {root}")

    results: List[FileItem] = []

    for dirpath, dirnames, filenames in os.walk(root):
        current_dir = Path(dirpath)

        # Filter ignored directories (modifying dirnames in place prevents os.walk from entering these directories)
        dirnames[:] = [
            d for d in dirnames
            if d not in ignore_dirs and (include_hidden or not d.startswith('.'))
        ]

        for filename in filenames:
            # Skip hidden files
            if not include_hidden and filename.startswith('.'):
                continue

            filepath = current_dir / filename

            # Progress callback
            if progress_callback:
                progress_callback(str(filepath))

            # Additional filter
            if file_filter and not file_filter(filepath):
                continue

            # Keyword matching
            if keyword:
                match_target = str(filepath.relative_to(root)) if match_path else filename
                if not contains(match_target, keyword, case_sensitive):
                    continue

            try:
                results.append(FileItem.from_path(filepath))
            except (OSError, PermissionError) as e:
                # Skip inaccessible files
                if progress_callback:
                    progress_callback(f"Warning: Cannot access {filepath}: {e}")

    return results


def scan_directory(
    directory: Path,
    suffix_filter: Optional[str] = None,
    include_hidden: bool = False,
    file_filter: Optional[Callable[[Path], bool]] = None
) -> List[FileItem]:
    """
    Scan single directory (non-recursive), for sequential naming feature

    Args:
        directory: Target directory
        suffix_filter: Suffix filter (e.g., ".jpg", must include dot)
        include_hidden: Whether to include hidden files
        file_filter: Additional file filter function

    Returns:
        File list
    """
    directory = Path(directory).resolve()
    if not directory.is_dir():
        raise ValueError(f"Directory does not exist: {directory}")

    results: List[FileItem] = []

    for item in directory.iterdir():
        # Only process files, not directories
        if not item.is_file():
            continue

        # Skip hidden files
        if not include_hidden and item.name.startswith('.'):
            continue

        # Suffix filter
        if suffix_filter and item.suffix.lower() != suffix_filter.lower():
            continue

        # Additional filter
        if file_filter and not file_filter(item):
            continue

        try:
            results.append(FileItem.from_path(item))
        except (OSError, PermissionError):
            # Skip inaccessible files
            continue

    return results


def list_suffixes(directory: Path, include_hidden: bool = False) -> List[str]:
    """
    List all file suffixes in the directory

    Args:
        directory: Target directory
        include_hidden: Whether to include hidden files

    Returns:
        Suffix list (deduplicated, sorted)
    """
    directory = Path(directory).resolve()
    if not directory.is_dir():
        return []

    suffixes = set()
    for item in directory.iterdir():
        if item.is_file():
            if not include_hidden and item.name.startswith('.'):
                continue
            if item.suffix:
                suffixes.add(item.suffix.lower())

    return sorted(suffixes)


def get_existing_names(directory: Path, case_insensitive: bool = True) -> set:
    """
    Get set of existing filenames in directory (for conflict detection)

    Args:
        directory: Target directory
        case_insensitive: Whether case-insensitive

    Returns:
        Filename set
    """
    directory = Path(directory).resolve()
    if not directory.is_dir():
        return set()

    names = set()
    for item in directory.iterdir():
        if item.is_file():
            name = item.name.casefold() if case_insensitive else item.name
            names.add(name)

    return names
