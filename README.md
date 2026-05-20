# 🔮 Prism Organizer

> A portable, lightweight CLI tool that scans, analyzes, and organizes files on Windows machines.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://python.org)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-0078d7.svg)]()
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)]()

## Features

- **🔍 Scan & Analyze** — Get a detailed report of any directory: file type breakdown, largest files, duplicates, junk files, and more
- **📁 Sort by Type** — Organize files into category folders (Images, Documents, Videos, Code, etc.)
- **📅 Sort by Date** — Organize files into `YYYY/Month/` date-based folders
- **🔎 Duplicate Detection** — 3-phase detection (size → partial hash → SHA-256) finds exact duplicates fast
- **🧹 Cleanup** — Remove temp files, Word lock files, incomplete downloads, and flag large installers
- **☁️ Cloud Drive Detection** — Auto-detects OneDrive, Google Drive, Dropbox, etc. and skips them to prevent sync conflicts
- **📝 Custom Rules** — Define your own rules in YAML to match and organize files your way
- **🔄 Undo** — Every operation is logged and fully reversible
- **👁️ Dry-Run Preview** — Always shows a preview before making any changes

## Quick Start

### Prerequisites
- Python 3.8 or later ([download](https://python.org))

### Installation

**Option 1: One-click setup (Windows)**
```
Double-click setup.bat
```

**Option 2: Manual install**
```bash
pip install -e .
```

**Option 3: From another machine**
1. Copy the entire `organizer/` folder to the target machine
2. Run `setup.bat` or `pip install -e .`

### Verify Installation
```bash
prism-organizer --version
prism-organizer --help
```

## Usage

### Scan a Directory
Analyze what's in a directory:
```bash
prism-organizer scan ~/Downloads
prism-organizer scan ~/Downloads --verbose
```

### Sort Files by Type
Organize files into category folders (Images, Documents, Videos, etc.):
```bash
prism-organizer sort ~/Downloads
prism-organizer sort ~/Downloads --by type
```

### Sort Files by Date
Organize files into year/month folders:
```bash
prism-organizer sort ~/Downloads --by date
```

### Find Duplicates
```bash
prism-organizer dupes ~/Downloads             # Report only
prism-organizer dupes ~/Downloads --clean      # Report + prompt to remove
```

### Clean Junk Files
Remove temp files, Word lock files, incomplete downloads:
```bash
prism-organizer clean ~/Downloads
```

### Apply Custom Rules
```bash
prism-organizer rules ~/Downloads
```

### Undo Last Operation
```bash
prism-organizer undo            # Undo last operation
prism-organizer undo --list     # List recent operations
```

## Configuration

Configuration is stored at `~/.prism-organizer/config.yaml`.

A default config is created on first run. You can also copy and customize `config.example.yaml`.

### Key Settings

| Setting | Description | Default |
|---------|-------------|---------|
| `default_paths` | Directories to organize when no path given | Downloads, Desktop |
| `categories` | Extension-to-category mappings | 13 categories |
| `junk_patterns` | Patterns for auto-cleanup | ~$*, *.crdownload, etc. |
| `cloud_drives.auto_detect` | Auto-skip cloud sync folders | `true` |
| `installer_detection.enabled` | Flag large installers | `true` |
| `screenshot_rules.enabled` | Auto-sort screenshots by date | `true` |
| `duplicates.method` | Detection method (hash/name+size) | `hash` |
| `duplicates.keep` | Which copy to keep | `oldest` |
| `duplicates.min_size` | Minimum size to check | `1MB` |

### Custom Rules

Define rules in your config to automate file organization:

```yaml
custom_rules:
  - name: "Archive old installers"
    match:
      extension: [.exe, .msi]
      size_gt: "100MB"
      older_than: "30d"
    action: move
    destination: "~/Archive/Installers/"

  - name: "Organize social media images"
    match:
      extension: [.jpg, .png]
      name_matches: "^[0-9a-f]{8}-[0-9a-f]{4}-.*"
    action: move
    destination: "~/Pictures/Social Media/"

  - name: "Clean incomplete downloads"
    match:
      extension: .crdownload
    action: delete
```

#### Match Conditions
| Condition | Description | Example |
|-----------|-------------|---------|
| `extension` | File extension (single or list) | `.pdf` or `[.jpg, .png]` |
| `name_contains` | Substring in filename | `"thesis"` |
| `name_matches` | Regex pattern on filename | `"^IMG_\\d+"` |
| `size_gt` | File larger than | `"100MB"` |
| `size_lt` | File smaller than | `"1KB"` |
| `older_than` | Modified more than X ago | `"30d"`, `"2w"` |
| `newer_than` | Modified less than X ago | `"7d"` |
| `path_contains` | Substring in full path | `"Downloads"` |

#### Actions
| Action | Description |
|--------|-------------|
| `move` | Move to destination folder |
| `copy` | Copy to destination |
| `rename` | Rename using pattern |
| `delete` | Remove (backed up first) |
| `archive` | Compress into zip |

## Safety Features

- **🔒 Dry-run by default** — Every command shows a preview and asks for confirmation
- **📦 Backups before delete** — Deleted files go to `.prism-organizer_backup/` first
- **📝 Full operation logs** — Every action is logged to `~/.prism-organizer/logs/`
- **↩️ Undo support** — Reverse any operation with `prism-organizer undo`
- **☁️ Cloud drive protection** — Auto-skips synced folders to prevent conflicts

## Deploying to Another Machine

1. Zip the entire `organizer/` project folder
2. Transfer to the target machine
3. Unzip and run `setup.bat`
4. Done! Use `prism-organizer` from any terminal

The only requirement is **Python 3.8+** on the target machine.

## Project Structure

```
prism_organizer/
├── cli.py           # CLI commands and argument parsing
├── config.py        # Configuration loader
├── scanner.py       # Filesystem analyzer
├── sorter.py        # Sort by type/date
├── duplicates.py    # 3-phase duplicate detection
├── rules.py         # Custom rule engine
├── cleaner.py       # Junk file cleanup
├── cloud_drives.py  # Cloud drive detection
├── preview.py       # Dry-run preview UI
├── executor.py      # File operations + logging
└── undo.py          # Undo/rollback
```

## License

MIT License © 2026 Jeff
