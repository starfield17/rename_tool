"""
core - Batch Rename Tool Core Module

Provides core functionalities such as file scanning, rename plan generation, execution, etc.
"""

from .models_fs import (
    FileItem,
    RenameOp,
    RenamePlan,
    RenameOptions,
    SortKey,
    ConflictPolicy,
)

from .scan_files import (
    scan_recursive,
    scan_directory,
    list_suffixes,
    get_existing_names,
)

from .text_match import (
    contains,
    replace_text,
    is_valid_filename,
    sanitize_filename,
)

from .sort_rules import (
    sort_files,
    sort_by_path,
    get_sort_key,
)

from .plan_rename import (
    plan_replace_rename,
    plan_sequence_rename,
    validate_plan,
    ConflictResolver,
)

from .exec_rename import (
    execute_rename,
    RenameResult,
    cleanup_temp_files,
)

from .safety_checks import (
    check_writable,
    check_path_length,
    check_rename_op,
)

__all__ = [
    # Data models
    "FileItem",
    "RenameOp",
    "RenamePlan",
    "RenameOptions",
    "SortKey",
    "ConflictPolicy",
    "RenameResult",

    # Scanning
    "scan_recursive",
    "scan_directory",
    "list_suffixes",
    "get_existing_names",

    # Text processing
    "contains",
    "replace_text",
    "is_valid_filename",
    "sanitize_filename",

    # Sorting
    "sort_files",
    "sort_by_path",
    "get_sort_key",

    # Planning
    "plan_replace_rename",
    "plan_sequence_rename",
    "validate_plan",
    "ConflictResolver",

    # Execution
    "execute_rename",
    "cleanup_temp_files",

    # Safety checks
    "check_writable",
    "check_path_length",
    "check_rename_op",
]
