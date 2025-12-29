"""
safety_checks.py - Safety Check Module

Provides various safety checks before file operations
"""

from pathlib import Path
from typing import Tuple, Optional, List
import os
import platform

from .text_match import is_valid_filename


def check_writable(path: Path) -> Tuple[bool, Optional[str]]:
    """
    Check if path is writable

    Args:
        path: Path to check

    Returns:
        (is_writable, error_reason)
    """
    if path.exists():
        # File exists, check if writable
        if not os.access(path, os.W_OK):
            return False, f"File is not writable: {path}"
    else:
        # File doesn't exist, check if parent directory is writable
        parent = path.parent
        if not parent.exists():
            return False, f"Parent directory does not exist: {parent}"
        if not os.access(parent, os.W_OK):
            return False, f"Directory is not writable: {parent}"

    return True, None


def check_path_length(path: Path, max_length: int = 260) -> Tuple[bool, Optional[str]]:
    """
    Check if path length exceeds limit (mainly for Windows)

    Args:
        path: Path to check
        max_length: Maximum length

    Returns:
        (is_valid, error_reason)
    """
    path_str = str(path)
    if len(path_str) > max_length:
        return False, f"Path length ({len(path_str)}) exceeds limit ({max_length}): {path}"
    return True, None


def check_rename_op(src: Path, dst: Path) -> Tuple[bool, Optional[str]]:
    """
    Check if a single rename operation is safe

    Args:
        src: Source path
        dst: Destination path

    Returns:
        (is_safe, error_reason)
    """
    # Check if source file exists
    if not src.exists():
        return False, f"Source file does not exist: {src}"

    # Check if source is a file
    if not src.is_file():
        return False, f"Source path is not a file: {src}"

    # Check destination filename validity
    valid, error = is_valid_filename(dst.name)
    if not valid:
        return False, error

    # Check path length
    if platform.system() == "Windows":
        valid, error = check_path_length(dst)
        if not valid:
            return False, error

    # Check writability
    valid, error = check_writable(src)
    if not valid:
        return False, error

    return True, None


def check_batch_rename(ops: List[Tuple[Path, Path]]) -> List[Tuple[Path, Path, str]]:
    """
    Batch check rename operations

    Args:
        ops: Operation list [(src, dst), ...]

    Returns:
        Error list [(src, dst, error), ...]
    """
    errors = []
    for src, dst in ops:
        valid, error = check_rename_op(src, dst)
        if not valid:
            errors.append((src, dst, error))
    return errors


def is_same_filesystem(path1: Path, path2: Path) -> bool:
    """
    Check if two paths are on the same filesystem

    Args:
        path1: Path 1
        path2: Path 2

    Returns:
        Whether on the same filesystem
    """
    try:
        # Get parent directory (if file doesn't exist)
        p1 = path1 if path1.exists() else path1.parent
        p2 = path2 if path2.exists() else path2.parent

        stat1 = os.stat(p1)
        stat2 = os.stat(p2)

        # Compare device IDs
        return stat1.st_dev == stat2.st_dev
    except (OSError, FileNotFoundError):
        return False
