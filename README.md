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
- **🖼️ Near-Duplicate Images** — Perceptual hashing finds visually similar (not just byte-identical) images
- **🧹 Cleanup** — Remove temp files, Word lock files, incomplete downloads, and flag large installers
- **☁️ Cloud Drive Detection** — Auto-detects OneDrive, Google Drive, Dropbox, etc. and skips them to prevent sync conflicts
- **📝 Custom Rules** — Define your own rules in YAML to match and organize files your way
- **🤖 AI Classification** — AI-powered category suggestions for unknown files (BYOK — bring your own key, or use a local LLM)
- **🔄 Undo** — Every operation is logged and fully reversible
- **👁️ Dry-Run Preview** — Always shows a preview before making any changes
- **⚡ Parallel Processing** — Multi-threaded scanning and hashing for large directories
- **🎨 Rich Terminal UI** — Beautiful tables, panels, and progress bars when the `rich` library is installed (optional)
- **👀 Watch Mode** — Monitor directories in real-time and auto-organize new files
- **📅 Scheduled Tasks** — Windows Task Scheduler integration for periodic organization

## Quick Start

### Prerequisites
- Python 3.8 or later ([download](https://python.org))

### Installation

Choose one of the following options:

#### Option 1: Direct from GitHub (Recommended)
```bash
pip install git+https://github.com/J-Akiru5/prism-organizer.git
```

#### Option 2: Pre-packaged ZIP Release
1. Download the release `prism-organizer.zip` file.
2. Extract the ZIP file onto your machine.
3. Double-click `setup.bat` to install it automatically (or run `pip install -e .` in your terminal inside the directory).

#### Option 3: Clone the Repository (For Developers)
```bash
git clone https://github.com/J-Akiru5/prism-organizer.git
cd prism-organizer
pip install -e .
```

### Install Optional Features

```bash
# Rich terminal UI (recommended)
pip install rich

# Perceptual image duplicate detection
pip install imagehash Pillow

# AI classification & renaming (any OpenAI-compatible provider)
pip install openai

# Real-time directory watching
pip install watchdog

# Or install everything at once
pip install -e . && pip install rich imagehash Pillow openai watchdog
```

### Verify Installation
```bash
prism-organizer --version
prism-organizer --help
```

> [!NOTE]
> **PATH Troubleshooting**: If Windows shows a warning that the script is installed in a directory which is not on your `PATH`, you can run the tool directly using Python:
> ```bash
> python -m prism_organizer --help
> ```
> To fix the `prism-organizer` command permanently, add Python's `Scripts` directory (e.g., `C:\Users\<YourUsername>\AppData\Roaming\Python\Python313\Scripts`) to your system Environment Variables `PATH`.

## Usage

### Scan a Directory
```bash
prism-organizer scan ~/Downloads
prism-organizer scan ~/Downloads --verbose
prism-organizer scan ~/Downloads -w 8      # Use 8 worker threads
```

### Sort Files by Type
```bash
prism-organizer sort ~/Downloads
prism-organizer sort ~/Downloads --by type
```

### Sort Files by Date
```bash
prism-organizer sort ~/Downloads --by date
```

### Find Duplicates
```bash
prism-organizer dupes ~/Downloads                           # Report only
prism-organizer dupes ~/Downloads --clean                   # Report + prompt to remove
prism-organizer dupes ~/Downloads --perceptual              # Also find visually similar images
prism-organizer dupes ~/Downloads --clean --perceptual      # Both exact + near-duplicate
```

### Clean Junk Files
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

### AI Classification

> **Requires:** `pip install openai`
> **Config:** `ai.enabled: true` in your config

```bash
prism-organizer ai-classify ~/Downloads                        # Suggest categories for unknown files
prism-organizer ai-classify ~/Downloads --rename                # Also suggest descriptive filenames
```

### Watch Mode (Real-Time)

> **For best experience:** `pip install watchdog`
> Without watchdog, a polling fallback is used (10-second interval).

```bash
prism-organizer watch ~/Downloads                    # Default: auto-sort new files
prism-organizer watch ~/Downloads --action clean     # Auto-clean new files
prism-organizer watch ~/Downloads --action all       # Sort + clean new files
```

### Scheduled Tasks (Windows Task Scheduler)

```bash
prism-organizer schedule add ~/Downloads --command sort --interval daily --at 09:00
prism-organizer schedule list
prism-organizer schedule remove
```

## AI Integration — Bring Your Own Key (BYOK) / Local LLM

Prism Organizer supports **any OpenAI-compatible API** — this means you can use cloud providers (OpenAI, Anthropic via proxy) OR local LLMs (Ollama, LM Studio, vLLM) that expose an OpenAI-compatible endpoint.

**Yes, this is BYOK (Bring Your Own Key).** The tool never sends data to any service you don't configure. You choose the provider, model, and API key.

### Supported Providers

| Provider | Setup |
|----------|-------|
| **OpenAI API** | Set `provider: openai` and provide your API key |
| **Ollama** (local) | Set `provider: ollama` — no key needed, uses `http://localhost:11434/v1` |
| **LM Studio** (local) | Set `provider: lmstudio` — no key needed, uses `http://localhost:1234/v1` |
| **Any OpenAI-compatible** | Set `provider: openai` + `base_url` to your endpoint |

### Configuration

```yaml
ai:
  enabled: true
  provider: "openai"            # openai, ollama, or lmstudio
  model: "gpt-4o-mini"          # or "llama3.2", "phi-4", etc. for local models
  api_key: ""                   # Only needed for cloud providers (or set OPENAI_API_KEY env var)
  base_url: ""                  # Override for custom endpoints
  features:
    classify_unknown: true      # Suggest categories for unknown file extensions
    smart_rename: false         # Generate descriptive filenames for auto-named files
  min_confidence: 0.7           # Only act on suggestions above this confidence threshold
```

### Local LLM Examples

**Ollama** (free, runs locally):
```yaml
ai:
  enabled: true
  provider: "ollama"
  model: "llama3.2"             # Any model you've pulled in Ollama
  # No api_key or base_url needed — defaults to http://localhost:11434/v1
```

**LM Studio** (free, runs locally):
```yaml
ai:
  enabled: true
  provider: "lmstudio"
  model: "local-model"          # Name of the loaded model in LM Studio
  # No api_key needed — defaults to http://localhost:1234/v1
```

**Custom OpenAI-compatible endpoint** (e.g., vLLM, TGI):
```yaml
ai:
  enabled: true
  provider: "openai"
  model: "custom-model"
  base_url: "http://localhost:8000/v1"
  api_key: "sk-..."             # if required by your endpoint
```

### Security & Privacy

- All AI data stays within your configured provider.
- Only filenames, extensions, sizes, and short content previews (first ~500 chars of text files) are sent.
- No files are ever moved or renamed by AI — all suggestions go through the **dry-run → preview → confirm** pipeline.
- With a local LLM (Ollama/LM Studio), everything stays on your machine — zero data leaves your computer.

## Configuration

Configuration is stored at `~/.prism-organizer/config.yaml`.

A default config is created automatically on first run. You can also copy and customize `config.example.yaml`.

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
| `duplicates.perceptual_threshold` | Hamming distance for near-duplicate images | `5` |
| `ai.enabled` | Enable AI classification/renaming | `false` |
| `ai.provider` | LLM provider (`openai`, `ollama`, `lmstudio`) | `openai` |
| `ai.model` | Model name | `gpt-4o-mini` |
| `ai.min_confidence` | Minimum confidence to apply AI suggestions | `0.7` |
| `watcher.cooldown_seconds` | Min time between triggered watch actions | `10` |
| `watcher.min_file_age_seconds` | Wait before acting on new files | `5` |

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
- **🤖 AI always suggests, never acts** — AI classifications go through the preview/confirm pipeline

## Performance Tips

- Use `--workers` (or `-w`) to control thread count. Default is `min(32, cpu_count + 4)`.
- For mechanical hard drives, use fewer workers (`-w 2`) to avoid I/O thrashing.
- For SSDs with many small files, more workers (`-w 8` or higher) speeds things up significantly.
- Duplicate detection runs 3 phases automatically: phase 2 and 3 are parallelized when file counts exceed 50.

## Deploying to Another Machine

1. Zip the entire `prism_organizer/` project folder
2. Transfer to the target machine
3. Unzip and run `setup.bat`
4. Done! Use `prism-organizer` from any terminal

The only requirement is **Python 3.8+** on the target machine.

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
├── display.py       # Rich/colorama display abstraction
├── ai.py            # AI-powered classification & renaming
├── watcher.py       # Real-time directory watcher + scheduler
└── utils.py         # Shared utilities
```

## License

MIT License © 2026 Syntaxure Labs
