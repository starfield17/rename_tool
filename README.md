# Batch Rename Tool

A cross-platform batch file rename tool that supports both CLI and GUI usage.

## Features

### 1. Search and Replace Rename
- Recursively search for files containing specified keywords from a given folder root
- Supports case-sensitive/insensitive search
- Batch replace a string in filenames with another string
- Example: `sakura_01.realcugan.png` → `sakura_01.png`

### 2. Sequential Naming
- Rename files within a folder (non-recursive) according to rules
- Supports sorting by modification time, file size, filename, etc.
- Supports custom starting number, zero-padding digits, prefix
- Example: `1.jpg`, `2.jpg`, `3.jpg`... or `img_001.jpg`, `img_002.jpg`...

### 3. Automatic Conflict Handling
- Automatically detects and resolves filename conflicts
- Automatically adds `_1`, `_2`, `_3`... suffixes when conflicts occur
- Uses two-phase rename for safety (first to temporary name, then to final name)

## Installation

```bash
# Clone or download the project
cd rename_tool

# Install dependencies (PySide6 required for GUI)
pip install -r requirements.txt

# PySide6 can be omitted if only using CLI
```

## Usage

### GUI Mode (Default)

```bash
python main.py
```

Run directly to start the graphical interface, no parameters required.

### CLI Mode

#### CLI Interactive Mode
```bash
python main.py --cli
# or
python main.py -c
```

Enters menu-based interactive interface.

#### CLI Command Mode

##### Search Files
```bash
python main.py --cli search ./photos --keyword "realcugan"
python main.py -c search ./photos -k "realcugan" -c  # Case-sensitive
```

##### String Replace Rename
```bash
python main.py --cli replace ./photos --keyword "realcugan" --old ".realcugan" --new ""
python main.py -c replace ./photos -k "realcugan" -o ".realcugan" -n "" -d  # dry-run preview
python main.py -c replace ./photos -k "realcugan" -o ".realcugan" -n "" -y  # Skip confirmation
```

##### Sequential Naming
```bash
python main.py --cli sequence ./photos --suffix ".jpg" --sort mtime
python main.py -c sequence ./photos -s ".jpg" --sort mtime --start 1 --padding 3 --prefix "img_"
python main.py -c sequence ./photos -s ".jpg" --sort size -r  # Reverse sort by size
```

### CLI Interactive Mode

```bash
python main.py
```

Enters menu-based interactive interface, follow prompts.

### CLI Command Mode

#### Search Files
```bash
python main.py search ./photos --keyword "realcugan"
python main.py search ./photos -k "realcugan" -c  # Case-sensitive
```

#### String Replace Rename
```bash
python main.py replace ./photos --keyword "realcugan" --old ".realcugan" --new ""
python main.py replace ./photos -k "realcugan" -o ".realcugan" -n "" -d  # dry-run preview
python main.py replace ./photos -k "realcugan" -o ".realcugan" -n "" -y  # Skip confirmation
```

#### Sequential Naming
```bash
python main.py sequence ./photos --suffix ".jpg" --sort mtime
python main.py sequence ./photos -s ".jpg" --sort mtime --start 1 --padding 3 --prefix "img_"
python main.py sequence ./photos -s ".jpg" --sort size -r  # Reverse sort by size
```

## Project Structure

```
rename_tool/
├── main.py              # Main entry
├── requirements.txt     # Dependencies
├── README.md           # Documentation
├── core/               # Core modules
│   ├── __init__.py
│   ├── models_fs.py    # Data models
│   ├── scan_files.py   # File scanning
│   ├── text_match.py   # Text matching
│   ├── sort_rules.py   # Sorting rules
│   ├── plan_rename.py  # Rename planning
│   ├── exec_rename.py  # Executor
│   └── safety_checks.py # Safety checks
├── cli/                # CLI modules
│   ├── __init__.py
│   ├── cli_entry.py    # CLI entry
│   └── cli_interactive.py # Interactive mode
└── gui/                # GUI modules
    ├── __init__.py
    ├── gui_entry.py    # GUI entry
    ├── gui_mainwindow.py # Main window
    └── gui_workers.py  # Worker threads
```

## Conflict Handling Strategy

When target filenames already exist or multiple files would be renamed to the same name:

1. **Auto-numbering**: Conflicting filenames automatically receive `_1`, `_2`, `_3`... suffixes
2. **Two-phase rename**:
   - Phase 1: All files renamed to temporary names (`.__tmp_rename__xxx__original_name`)
   - Phase 2: Temporary names changed to final names
   - Safely handles name swaps (A→B, B→A) and circular rename scenarios

## Safety Features

- **Preview mode**: Preview all rename operations before execution
- **Conflict alerts**: Both GUI and CLI show which files were automatically renamed due to conflicts
- **Execution logs**: Each execution saves an operation log (JSON format)
- **Filename validation**: Automatically checks for Windows illegal characters, reserved names, etc.

## Cross-Platform Notes

- **Case sensitivity**: Windows/macOS default to case-insensitive; conflict detection adapts automatically
- **Creation time**: Linux ctime is not creation time; recommend using mtime (modification time) for sorting
- **Path length**: Windows has 260-character path limit; tool automatically checks

## License

MIT License
