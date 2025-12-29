"""
cli_entry.py - CLI Entry Point

Supports:
- Command-line argument mode
- Interactive mode
"""

import argparse
import sys
from pathlib import Path

from .cli_interactive import interactive_mode


def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser"""
    parser = argparse.ArgumentParser(
        prog="rename_tool",
        description="Batch Rename Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python -m cli.cli_entry
  
  # Search files
  python -m cli.cli_entry search ./photos --keyword "realcugan"
  
  # String replacement
  python -m cli.cli_entry replace ./photos --keyword "realcugan" --old ".realcugan" --new ""
  
  # Sequential naming
  python -m cli.cli_entry sequence ./photos --suffix ".jpg" --sort mtime
"""
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Subcommands")
    
    # search subcommand
    search_parser = subparsers.add_parser("search", help="Search files")
    search_parser.add_argument("directory", type=str, help="Search directory")
    search_parser.add_argument("--keyword", "-k", type=str, default="", help="Search keyword")
    search_parser.add_argument("--case-sensitive", "-c", action="store_true", help="Case-sensitive")
    search_parser.add_argument("--match-path", "-p", action="store_true", help="Match relative path")
    search_parser.add_argument("--include-hidden", action="store_true", help="Include hidden files")
    
    # replace subcommand
    replace_parser = subparsers.add_parser("replace", help="String replacement rename")
    replace_parser.add_argument("directory", type=str, help="Search directory")
    replace_parser.add_argument("--keyword", "-k", type=str, default="", help="Search keyword")
    replace_parser.add_argument("--old", "-o", type=str, required=True, help="String to replace")
    replace_parser.add_argument("--new", "-n", type=str, default="", help="Replacement string")
    replace_parser.add_argument("--case-sensitive", "-c", action="store_true", help="Case-sensitive")
    replace_parser.add_argument("--dry-run", "-d", action="store_true", help="Preview only, do not execute")
    replace_parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")
    
    # sequence subcommand
    seq_parser = subparsers.add_parser("sequence", help="Sequential naming")
    seq_parser.add_argument("directory", type=str, help="Target directory")
    seq_parser.add_argument("--suffix", "-s", type=str, help="File suffix filter (e.g., .jpg)")
    seq_parser.add_argument("--sort", type=str, default="mtime", 
                           choices=["mtime", "size", "name", "ctime"], help="Sort method")
    seq_parser.add_argument("--reverse", "-r", action="store_true", help="Reverse sort")
    seq_parser.add_argument("--start", type=int, default=1, help="Starting number")
    seq_parser.add_argument("--padding", type=int, default=0, help="Zero-padding digits")
    seq_parser.add_argument("--prefix", type=str, default="", help="Prefix")
    seq_parser.add_argument("--dry-run", "-d", action="store_true", help="Preview only, do not execute")
    seq_parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")
    
    return parser


def cmd_search(args):
    """Handle search command"""
    from core import scan_recursive
    
    directory = Path(args.directory).resolve()
    if not directory.is_dir():
        print(f"Error: Directory does not exist: {directory}")
        return 1
    
    print(f"Search directory: {directory}")
    print(f"Keyword: {args.keyword or '(all)'}")
    print(f"Case-sensitive: {args.case_sensitive}")
    print()
    
    files = scan_recursive(
        directory,
        keyword=args.keyword,
        case_sensitive=args.case_sensitive,
        match_path=args.match_path,
        include_hidden=args.include_hidden,
    )
    
    if not files:
        print("No matching files found")
        return 0
    
    print(f"Found {len(files)} files:")
    print("-" * 80)
    for f in files:
        rel_path = f.relative_to(directory)
        size_kb = f.size / 1024
        print(f"  {rel_path:<50} {size_kb:>10.1f} KB")
    print("-" * 80)
    
    return 0


def cmd_replace(args):
    """Handle replace command"""
    from core import scan_recursive, plan_replace_rename, execute_rename, RenameOptions
    
    directory = Path(args.directory).resolve()
    if not directory.is_dir():
        print(f"Error: Directory does not exist: {directory}")
        return 1
    
    # Search files
    print(f"Search directory: {directory}")
    files = scan_recursive(
        directory,
        keyword=args.keyword,
        case_sensitive=args.case_sensitive,
    )
    
    if not files:
        print("No matching files found")
        return 0
    
    print(f"Found {len(files)} files")
    
    # Generate plan
    options = RenameOptions()
    plan = plan_replace_rename(
        files,
        old_str=args.old,
        new_str=args.new,
        case_sensitive=args.case_sensitive,
        options=options,
    )
    
    if plan.errors:
        print("Errors:")
        for err in plan.errors:
            print(f"  - {err}")
        return 1
    
    if not plan.valid_ops:
        print("No files need renaming")
        return 0
    
    # Show preview
    print()
    print(f"Will perform {plan.total_count} rename operations:")
    print("-" * 80)
    for op in plan.valid_ops[:20]:
        note = f" ({op.note})" if op.note else ""
        print(f"  {op.src.name:<40} -> {op.dst.name}{note}")
    if len(plan.valid_ops) > 20:
        print(f"  ... and {len(plan.valid_ops) - 20} more operations")
    print("-" * 80)
    
    if plan.warnings:
        print("Warnings:")
        for warn in plan.warnings:
            print(f"  - {warn}")
    
    # Confirmation
    if args.dry_run:
        print("\n[Preview mode] Will not actually execute")
        return 0
    
    if not args.yes:
        confirm = input("\nConfirm execution? (y/N): ").strip().lower()
        if confirm != 'y':
            print("Cancelled")
            return 0
    
    # Execute
    print("\nExecuting...")
    result = execute_rename(plan, dry_run=False)
    print(result.summary())
    
    return 0 if result.failed_count == 0 else 1


def cmd_sequence(args):
    """Handle sequence command"""
    from core import scan_directory, plan_sequence_rename, execute_rename, RenameOptions, SortKey
    
    directory = Path(args.directory).resolve()
    if not directory.is_dir():
        print(f"Error: Directory does not exist: {directory}")
        return 1
    
    # Scan files
    print(f"Scan directory: {directory}")
    files = scan_directory(directory, suffix_filter=args.suffix)
    
    if not files:
        print("No matching files found")
        return 0
    
    print(f"Found {len(files)} files")
    
    # Map sort method
    sort_map = {
        "mtime": SortKey.MTIME,
        "size": SortKey.SIZE,
        "name": SortKey.NAME,
        "ctime": SortKey.CTIME,
    }
    sort_key = sort_map.get(args.sort, SortKey.MTIME)
    
    # Generate plan
    options = RenameOptions()
    plan = plan_sequence_rename(
        files,
        sort_by=sort_key,
        reverse=args.reverse,
        start=args.start,
        padding=args.padding,
        prefix=args.prefix,
        options=options,
    )
    
    if plan.errors:
        print("Errors:")
        for err in plan.errors:
            print(f"  - {err}")
        return 1
    
    if not plan.valid_ops:
        print("No files need renaming")
        return 0
    
    # Show preview
    print()
    print(f"Will perform {plan.total_count} rename operations:")
    print("-" * 80)
    for op in plan.valid_ops[:20]:
        note = f" ({op.note})" if op.note else ""
        print(f"  {op.src.name:<40} -> {op.dst.name}{note}")
    if len(plan.valid_ops) > 20:
        print(f"  ... and {len(plan.valid_ops) - 20} more operations")
    print("-" * 80)
    
    # Confirmation
    if args.dry_run:
        print("\n[Preview mode] Will not actually execute")
        return 0
    
    if not args.yes:
        confirm = input("\nConfirm execution? (y/N): ").strip().lower()
        if confirm != 'y':
            print("Cancelled")
            return 0
    
    # Execute
    print("\nExecuting...")
    result = execute_rename(plan, dry_run=False)
    print(result.summary())
    
    return 0 if result.failed_count == 0 else 1


def main():
    """Main entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    if args.command is None:
        # No subcommand, enter interactive mode
        return interactive_mode()
    
    # Handle subcommands
    if args.command == "search":
        return cmd_search(args)
    elif args.command == "replace":
        return cmd_replace(args)
    elif args.command == "sequence":
        return cmd_sequence(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())