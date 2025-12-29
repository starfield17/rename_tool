#!/usr/bin/env python3
"""
Batch Renaming Tool - Main Entry

Supports:
- GUI mode (default startup)
- CLI mode (--cli or -c parameter)

Usage:
    python main.py                    # GUI mode (default)
    python main.py --cli              # CLI interactive mode
    python main.py -c                 # CLI interactive mode
    python main.py --cli search ./dir # CLI command mode
    python main.py -c replace ./dir ... # CLI command mode
    python main.py -c sequence ./dir ... # CLI command mode
"""

import sys
import argparse
from pathlib import Path

# Ensure the current directory is in the Python path
sys.path.insert(0, str(Path(__file__).parent))


def main():
    """Main entry point"""
    # Check if CLI should be started
    if "--cli" in sys.argv or "-c" in sys.argv:
        # Remove --cli parameter
        sys.argv = [arg for arg in sys.argv if arg not in ("--cli", "-c")]
        
        # CLI mode
        from cli import main as cli_main
        return cli_main()
    
    # Default to starting GUI
    try:
        from gui import main as gui_main
        return gui_main()
    except ImportError as e:
        print(f"Error: Unable to start GUI, please ensure PySide6 is installed")
        print(f"Detailed error: {e}")
        print("\nInstall command: pip install PySide6")
        print("\nTo use CLI mode, run:")
        print("    python main.py --cli")
        print("or  python main.py -c")
        return 1


if __name__ == "__main__":
    sys.exit(main())