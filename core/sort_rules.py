"""
sort_rules.py - Sorting Rules Module

Provides various file sorting methods
"""

from typing import List, Callable
from .models_fs import FileItem, SortKey


def get_sort_key(sort_by: SortKey, reverse: bool = False) -> Callable[[FileItem], tuple]:
    """
    Get sort key function

    Args:
        sort_by: Sorting method
        reverse: Whether reverse (this parameter is only for record, actual reversal is handled in sorted())

    Returns:
        Sort key function
    """
    if sort_by == SortKey.MTIME:
        return lambda f: (f.mtime, f.name.lower())
    elif sort_by == SortKey.SIZE:
        return lambda f: (f.size, f.name.lower())
    elif sort_by == SortKey.NAME:
        return lambda f: f.name.lower()
    elif sort_by == SortKey.CTIME:
        return lambda f: (f.ctime, f.name.lower())
    else:
        return lambda f: f.name.lower()


def sort_files(
    files: List[FileItem],
    sort_by: SortKey = SortKey.MTIME,
    reverse: bool = False
) -> List[FileItem]:
    """
    Sort file list

    Args:
        files: File list
        sort_by: Sorting method
        reverse: Whether to sort in reverse

    Returns:
        Sorted file list (new list)
    """
    key_func = get_sort_key(sort_by)
    return sorted(files, key=key_func, reverse=reverse)


def sort_by_path(files: List[FileItem], reverse: bool = False) -> List[FileItem]:
    """
    Sort by path (for ensuring stable processing order)

    Args:
        files: File list
        reverse: Whether to sort in reverse

    Returns:
        Sorted file list
    """
    return sorted(files, key=lambda f: str(f.path).lower(), reverse=reverse)
