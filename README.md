# 🔮 Prism Organizer

> A portable, beautiful CLI tool that scans, analyzes, and organizes files on Windows.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://python.org)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-0078d7.svg)]()
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)]()
[![npm](https://img.shields.io/npm/v/prism-organizer?color=red)](https://www.npmjs.com/package/prism-organizer)

## Features

- **🔍 Scan & Analyze** — Detailed reports with file type breakdown, largest files, duplicates, junk, and more
- **📁 Sort by Type** — Organize files into category folders (Images, Documents, Videos, Code, etc.)
- **📅 Sort by Date** — Organize files into `YYYY/Month/` folders
- **🔎 Duplicate Detection** — 3-phase detection (size → partial hash → SHA-256) finds exact duplicates fast
- **🖼️ Near-Duplicate Images** — Perceptual hashing finds visually similar images
- **🧹 Cleanup** — Remove temp files, lock files, incomplete downloads, large installers
- **☁️ Cloud Drive Detection** — Auto-detects OneDrive, Google Drive, Dropbox, etc. and skips them
- **📝 Custom Rules** — Define your own rules in YAML to organize files your way
- **🤖 AI Classification** — AI-powered category suggestions (BYOK or local LLM)
- **🔄 Undo** — Every operation is logged and fully reversible
- **👁️ Dry-Run Preview** — Always previews before making changes
- **⚡ Parallel Processing** — Multi-threaded scanning and hashing
- **🎨 Beautiful Terminal UI** — Rich tables, panels, progress bars with a cyan/purple theme
- **🎮 Interactive TUI Dashboard** — Arrow-key menus, checkboxes, live panels (`prism-organizer tui`)
- **👀 Watch Mode** — Real-time directory monitoring with auto-organization
- **📅 Scheduled Tasks** — Windows Task Scheduler integration

## Quick Start

### Prerequisites
- **Python 3.8+** ([download](https://python.org))
- **Node.js 16+** (for npm install only)

### Installation

```bash
# ── NPM (Recommended) ─────────────────────────────────
npm install -g prism-organizer

# ── Pip ───────────────────────────────────────────────
pip install git+https://github.com/J-Akiru5/prism-organizer.git

# ── Clone & Develop ───────────────────────────────────
git clone https://github.com/J-Akiru5/prism-organizer.git
cd prism-organizer && pip install -e .
```

### Verify Installation
```bash
prism-organizer --version
prism-organizer --help
```

> **PATH Troubleshooting**: If the command isn't recognized, run: `python -m prism_organizer --help`

## Usage

### Scan a Directory
```bash
prism-organizer scan ~/Downloads
prism-organizer scan ~/Downloads --verbose -w 8
```

### Sort Files
```bash
prism-organizer sort ~/Downloads                  # Sort by type (default)
prism-organizer sort ~/Downloads --by date        # Sort by modification date
```

### Find Duplicates
```bash
prism-organizer dupes ~/Downloads                 # Report only
prism-organizer dupes ~/Downloads --clean          # Report + prompt to remove
prism-organizer dupes ~/Downloads --perceptual     # Also find visually similar images
prism-organizer dupes ~/Downloads --clean --perceptual
```

### Clean Junk Files
```bash
prism-organizer clean ~/Downloads
```

### Custom Rules
```bash
prism-organizer rules ~/Downloads
```

### Undo
```bash
prism-organizer undo            # Undo last operation
prism-organizer undo --list     # List recent operations
```

### AI Classification
```bash
prism-organizer ai-classify ~/Downloads             # Suggest categories
prism-organizer ai-classify ~/Downloads --rename     # Also suggest filenames
```

### Watch Mode
```bash
prism-organizer watch ~/Downloads                    # Auto-sort new files
prism-organizer watch ~/Downloads --action clean     # Auto-clean new files
prism-organizer watch ~/Downloads --action all       # Sort + clean
```

### Scheduled Tasks
```bash
prism-organizer schedule add ~/Downloads --command sort --interval daily --at 09:00
prism-organizer schedule list
prism-organizer schedule remove
```

## Interactive TUI Dashboard

Launch the full interactive dashboard with arrow-key menus and live panels:

```bash
prism-organizer tui
```

The TUI provides:
- **Arrow-key navigation** — select directories, commands, and options with arrow keys
- **Live panels** — activity log, quick stats, and menu side-by-side
- **Keyboard shortcuts** — every function is a single keystroke away (`1`=scan, `2`=sort, `3`=dupes, etc.)
- **Zero subcommand memorization** — discover all features from the menu

```
╔══════════════════════════════════════════════════════╗
║  🔮  Prism Organizer v1.1.0                         ║
║  scan  |  sort  |  dupes  |  clean  |  rules  |  ai ║
╠══════════════════════════╦═══════════════════════════╣
║  📋  Main Menu           ║  📊  Quick Stats         ║
║  🔍 [1]  Scan directory  ║  Downloads: 247 files    ║
║  📁 [2]  Sort files      ║  Desktop: 89 files       ║
║  🔎 [3]  Find duplicates ║                          ║
║  🧹 [4]  Clean junk      ║  📜  Activity Log        ║
║  📝 [5]  Apply rules     ║  12:34 Sorted 15 files   ║
║  🤖 [6]  AI classify     ║  12:30 Cleaned 3 items   ║
║  👀 [7]  Watch mode      ║  12:25 Dupe check: 2 grp ║
║  ↩️ [8]  Undo last       ║                          ║
║  [S] Schedule  [H] Help  [Q] Quit                   ║
╚══════════════════════════╩═══════════════════════════╝
```

> Use `--no-interactive` to disable arrow-key prompts and use plain text input:
> ```bash
> prism-organizer sort ~/Downloads --no-interactive
> ```

## AI Integration — BYOK / Local LLM

Prism Organizer supports **any OpenAI-compatible API**. Use your own API key (BYOK) or a local LLM (Ollama, LM Studio, vLLM).

### Configuration
```yaml
ai:
  enabled: true
  provider: "openai"            # openai, ollama, or lmstudio
  model: "gpt-4o-mini"
  api_key: ""                   # or set OPENAI_API_KEY env var
  features:
    classify_unknown: true
    smart_rename: false
  min_confidence: 0.7
```

### Local LLM Example (Ollama)
```yaml
ai:
  enabled: true
  provider: "ollama"
  model: "llama3.2"
  # No api_key needed — runs entirely on your machine
```

## Configuration

Config stored at `~/.prism-organizer/config.yaml`. Auto-created on first run.

### Key Settings

| Setting | Description | Default |
|---------|-------------|---------|
| `default_paths` | Directories to organize | Downloads, Desktop |
| `categories` | Extension-to-category mappings | 13 categories |
| `junk_patterns` | Patterns for auto-cleanup | ~$*, *.crdownload, etc. |
| `duplicates.perceptual_threshold` | Hamming distance for near-dupes | `5` |
| `ai.enabled` | Enable AI classification | `false` |
| `ai.provider` | LLM provider (`openai`, `ollama`, `lmstudio`) | `openai` |
| `ai.min_confidence` | Minimum confidence to apply suggestions | `0.7` |
| `watcher.cooldown_seconds` | Min time between watch actions | `10` |
| `watcher.min_file_age_seconds` | Wait before acting on new files | `5` |

## Safety Features

- **🔒 Dry-run by default** — Every command shows a preview before executing
- **📦 Backups before delete** — Files go to `.prism-organizer_backup/` first
- **📝 Full operation logs** — Every action logged to `~/.prism-organizer/logs/`
- **↩️ Undo support** — Reverse any operation with `prism-organizer undo`
- **☁️ Cloud drive protection** — Auto-skips synced folders
- **🤖 AI always suggests, never acts** — Classifications go through preview/confirm

## Project Structure

```
prism_organizer/
├── cli.py           # CLI commands and argument parsing
├── config.py        # Configuration loader
├── scanner.py       # Filesystem analyzer (parallel)
├── sorter.py        # Sort by type/date
├── duplicates.py    # 3-phase + perceptual duplicate detection
├── rules.py         # Custom rule engine
├── cleaner.py       # Junk file cleanup
├── cloud_drives.py  # Cloud drive detection
├── preview.py       # Dry-run preview UI
├── executor.py      # File operations + logging
├── undo.py          # Undo/rollback
├── display.py       # Rich-themed display layer
├── interactive.py   # Arrow-key menus, checkboxes, wizards
├── tui.py           # Interactive TUI dashboard
├── ai.py            # AI-powered classification & renaming
├── watcher.py       # Real-time watcher + scheduler
└── utils.py         # Shared utilities
```

## License

MIT License © 2026 Syntaxure Labs
