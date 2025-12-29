"""
cli_interactive.py - Interactive CLI

Provides a menu-style interactive interface
"""

import sys
from pathlib import Path
from typing import Optional, List

# Import core module
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import (
    scan_recursive, scan_directory, list_suffixes,
    plan_replace_rename, plan_sequence_rename, execute_rename,
    RenameOptions, SortKey, FileItem
)


def clear_screen():
    """Clear screen"""
    import os
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header(title: str):
    """Print header"""
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)
    print()


def input_directory(prompt: str = "Please enter directory path") -> Optional[Path]:
    """Input and validate directory"""
    while True:
        path_str = input(f"{prompt} (q to return): ").strip()
        if path_str.lower() == 'q':
            return None
        
        path = Path(path_str).expanduser().resolve()
        if path.is_dir():
            return path
        else:
            print(f"Error: Directory does not exist: {path}")


def input_choice(prompt: str, choices: List[str], default: Optional[str] = None) -> Optional[str]:
    """Input choice"""
    choices_str = "/".join(choices)
    default_str = f" [{default}]" if default else ""
    
    while True:
        value = input(f"{prompt} ({choices_str}){default_str}: ").strip()
        if not value and default:
            return default
        if value.lower() == 'q':
            return None
        if value in choices:
            return value
        print(f"Invalid choice, please enter: {choices_str}")


def input_bool(prompt: str, default: bool = False) -> bool:
    """Input boolean value"""
    default_str = "Y/n" if default else "y/N"
    value = input(f"{prompt} ({default_str}): ").strip().lower()
    if not value:
        return default
    return value == 'y'


def input_int(prompt: str, default: int = 0, min_val: int = 0) -> int:
    """Input integer"""
    while True:
        value = input(f"{prompt} [{default}]: ").strip()
        if not value:
            return default
        try:
            num = int(value)
            if num < min_val:
                print(f"Value cannot be less than {min_val}")
                continue
            return num
        except ValueError:
            print("Please enter a valid integer")


def menu_search_replace():
    """Search and replace rename menu"""
    print_header("Search and Replace Rename")
    
    # Input directory
    directory = input_directory("Please enter search directory")
    if directory is None:
        return
    
    # Input search keyword
    keyword = input("Search keyword (leave empty to match all): ").strip()
    
    # Case sensitive
    case_sensitive = input_bool("Case sensitive", default=False)
    
    # Search
    print(f"\nSearching {directory} ...")
    files = scan_recursive(
        directory,
        keyword=keyword,
        case_sensitive=case_sensitive,
    )
    
    if not files:
        print("No matching files found")
        input("Press Enter to return...")
        return
    
    print(f"Found {len(files)} files")
    
    # Display partial results
    print("\nFirst 10 results:")
    for f in files[:10]:
        print(f"  - {f.relative_to(directory)}")
    if len(files) > 10:
        print(f"  ... and {len(files) - 10} more files")
    
    # Input replacement string
    print()
    old_str = input("String to replace: ").strip()
    if not old_str:
        print("Replacement string cannot be empty")
        input("Press Enter to return...")
        return
    
    new_str = input("Replace with (leave empty to delete): ").strip()
    
    # Generate plan
    print("\nGenerating rename plan...")
    options = RenameOptions()
    plan = plan_replace_rename(
        files,
        old_str=old_str,
        new_str=new_str,
        case_sensitive=case_sensitive,
        options=options,
    )
    
    if plan.errors:
        print("\nErrors:")
        for err in plan.errors:
            print(f"  - {err}")
        input("Press Enter to return...")
        return
    
    if not plan.valid_ops:
        print("No files need renaming")
        input("Press Enter to return...")
        return
    
    # Display plan
    print(f"\nWill perform {plan.total_count} rename operations:")
    print("-" * 70)
    for op in plan.valid_ops[:15]:
        note = f" [Conflict resolution]" if op.note else ""
        print(f"  {op.src.name:<30} -> {op.dst.name}{note}")
    if len(plan.valid_ops) > 15:
        print(f"  ... and {len(plan.valid_ops) - 15} more operations")
    print("-" * 70)
    
    if plan.conflict_count > 0:
        print(f"Note: {plan.conflict_count} files automatically renamed due to conflicts (adding _1, _2...)")
    
    # Confirm execution
    print()
    if not input_bool("Confirm execution", default=False):
        print("Cancelled")
        input("Press Enter to return...")
        return
    
    # Execute
    print("\nExecuting...")
    result = execute_rename(plan, dry_run=False)
    print()
    print(result.summary())
    
    input("\nPress Enter to return...")


def menu_sequence_rename():
    """Sequential naming menu"""
    print_header("Sequential Rename")
    
    # Input directory
    directory = input_directory("Please enter target directory")
    if directory is None:
        return
    
    # List available suffixes
    suffixes = list_suffixes(directory)
    if not suffixes:
        print("No files found in directory")
        input("Press Enter to return...")
        return
    
    print(f"\nAvailable file suffixes: {', '.join(suffixes)}")
    
    # Input suffix filter
    suffix_filter = input("File suffix filter (e.g., .jpg, leave empty for no filter): ").strip()
    if suffix_filter and not suffix_filter.startswith('.'):
        suffix_filter = '.' + suffix_filter
    
    # Scan files
    files = scan_directory(directory, suffix_filter=suffix_filter if suffix_filter else None)
    
    if not files:
        print("No matching files found")
        input("Press Enter to return...")
        return
    
    print(f"Found {len(files)} files")
    
    # Sorting method
    print("\nSorting method:")
    print("  1. mtime - Modification time")
    print("  2. size  - File size")
    print("  3. name  - File name")
    print("  4. ctime - Creation time")
    
    sort_choice = input_choice("Select sorting method", ["1", "2", "3", "4"], "1")
    if sort_choice is None:
        return
    
    sort_map = {"1": SortKey.MTIME, "2": SortKey.SIZE, "3": SortKey.NAME, "4": SortKey.CTIME}
    sort_key = sort_map[sort_choice]
    
    reverse = input_bool("Reverse sort", default=False)
    
    # Naming options
    start = input_int("Starting number", default=1, min_val=0)
    padding = input_int("Zero-padding digits (0=no padding)", default=0, min_val=0)
    prefix = input("Prefix (leave empty for no prefix): ").strip()
    
    # Generate plan
    print("\nGenerating rename plan...")
    options = RenameOptions()
    plan = plan_sequence_rename(
        files,
        sort_by=sort_key,
        reverse=reverse,
        start=start,
        padding=padding,
        prefix=prefix,
        options=options,
    )
    
    if plan.errors:
        print("\nErrors:")
        for err in plan.errors:
            print(f"  - {err}")
        input("Press Enter to return...")
        return
    
    if not plan.valid_ops:
        print("No files need renaming")
        input("Press Enter to return...")
        return
    
    # Display plan
    print(f"\nWill perform {plan.total_count} rename operations:")
    print("-" * 70)
    for op in plan.valid_ops[:15]:
        note = f" [Conflict resolution]" if op.note else ""
        print(f"  {op.src.name:<30} -> {op.dst.name}{note}")
    if len(plan.valid_ops) > 15:
        print(f"  ... and {len(plan.valid_ops) - 15} more operations")
    print("-" * 70)
    
    if plan.conflict_count > 0:
        print(f"Note: {plan.conflict_count} files automatically renamed due to conflicts (adding _1, _2...)")
    
    # Confirm execution
    print()
    if not input_bool("Confirm execution", default=False):
        print("Cancelled")
        input("Press Enter to return...")
        return
    
    # Execute
    print("\nExecuting...")
    result = execute_rename(plan, dry_run=False)
    print()
    print(result.summary())
    
    input("\nPress Enter to return...")


def menu_search_only():
    """Search only menu"""
    print_header("Search Files")
    
    # Input directory
    directory = input_directory("Please enter search directory")
    if directory is None:
        return
    
    # Input search keyword
    keyword = input("Search keyword (leave empty to match all): ").strip()
    
    # Case sensitive
    case_sensitive = input_bool("Case sensitive", default=False)
    
    # Search
    print(f"\nSearching {directory} ...")
    files = scan_recursive(
        directory,
        keyword=keyword,
        case_sensitive=case_sensitive,
    )
    
    if not files:
        print("No matching files found")
        input("Press Enter to return...")
        return
    
    # Display results
    print(f"\nFound {len(files)} files:")
    print("-" * 80)
    for i, f in enumerate(files):
        if i >= 50:
            print(f"... and {len(files) - 50} more files")
            break
        rel_path = f.relative_to(directory)
        size_kb = f.size / 1024
        print(f"  {rel_path:<55} {size_kb:>10.1f} KB")
    print("-" * 80)
    print(f"Total: {len(files)} files")
    
    input("\nPress Enter to return...")


def interactive_mode() -> int:
    """Interactive mode main loop"""
    while True:
        clear_screen()
        print_header("Batch Rename Tool")
        
        print("Please select function:")
        print()
        print("  1. Search files")
        print("  2. Search and replace rename")
        print("  3. Sequential rename")
        print()
        print("  q. Exit")
        print()
        
        choice = input("Please select (1/2/3/q): ").strip().lower()
        
        if choice == 'q':
            print("Goodbye!")
            return 0
        elif choice == '1':
            menu_search_only()
        elif choice == '2':
            menu_search_replace()
        elif choice == '3':
            menu_sequence_rename()
        else:
            print("Invalid choice")
            input("Press Enter to continue...")


if __name__ == "__main__":
    sys.exit(interactive_mode())