"""Comprehensive help and documentation system for Prism Organizer.

Provides rich, formatted help output for new users including command
reference, quick-start guide, configuration reference, keyboard
shortcuts, and tips.
"""


def get_quick_start() -> str:
    """One-minute onboarding guide."""
    return """
[bold cyan]Quick Start Guide[/bold cyan]

  [bold]1. Launch the TUI[/bold] (no arguments)
     > prism-organizer

  [bold]2. Select a directory[/bold] when prompted
     The [bold magenta]arrow keys[/bold magenta] and [bold magenta]Enter[/bold magenta] navigate the menus.

  [bold]3. Pick an action[/bold] by pressing a number key:
     [cyan][1][/cyan] Scan directory     [cyan][4][/cyan] Clean junk
     [cyan][2][/cyan] Sort files         [cyan][5][/cyan] Apply rules
     [cyan][3][/cyan] Find duplicates    [cyan][6][/cyan] AI classify

  [bold]4. Confirm[/bold] the preview before anything is changed.
     [green]Every operation is undoable.[/green]

  [bold]5. Press Enter[/bold] to return to the menu after each action.
     Press [cyan][Q][/cyan] to quit.
"""


def get_command_reference() -> str:
    """Full command-line reference."""
    return """
[bold cyan]Command Reference[/bold cyan]

  [bold]scan[/bold]        Analyze a directory
         prism-organizer scan ~/Downloads
         prism-organizer scan ~/Downloads --verbose -w 8

  [bold]sort[/bold]        Organize files into folders
         prism-organizer sort ~/Downloads                  # by type
         prism-organizer sort ~/Downloads --by date        # by date

  [bold]dupes[/bold]       Find duplicate files
         prism-organizer dupes ~/Downloads                 # report only
         prism-organizer dupes ~/Downloads --clean          # remove dupes
         prism-organizer dupes ~/Downloads --perceptual     # near-duplicates

  [bold]clean[/bold]       Remove junk / temp files
         prism-organizer clean ~/Downloads
         prism-organizer clean ~/Downloads --review-folder "~/Review/"

  [bold]rules[/bold]       Apply custom rules from config
         prism-organizer rules ~/Downloads

  [bold]ai-classify[/bold] AI-powered category suggestions
         prism-organizer ai-classify ~/Downloads
         prism-organizer ai-classify ~/Downloads --rename

  [bold]undo[/bold]        Reverse last operation
         prism-organizer undo
         prism-organizer undo --list

  [bold]watch[/bold]       Monitor directory in real-time
         prism-organizer watch ~/Downloads
         prism-organizer watch ~/Downloads --action clean

  [bold]schedule[/bold]    Manage scheduled tasks (Windows Task Scheduler)
         prism-organizer schedule add ~/Downloads --command sort --interval daily
         prism-organizer schedule list
         prism-organizer schedule remove

  [bold]tui[/bold]         Launch interactive dashboard
         prism-organizer tui

  [bold]help[/bold]        Show this help
         prism-organizer help
         prism-organizer help --topic tui
         prism-organizer help --topic config
"""


def get_tui_guide() -> str:
    """TUI keyboard shortcuts and navigation guide."""
    return """
[bold cyan]TUI Dashboard Guide[/bold cyan]

  The TUI (Terminal User Interface) is the default when you run
  [bold]prism-organizer[/bold] with no arguments.

  [bold magenta]Main Menu Shortcuts[/bold magenta]

    [cyan][1][/cyan]  Scan directory      [cyan][4][/cyan]  Clean junk files
    [cyan][2][/cyan]  Sort files          [cyan][5][/cyan]  Apply custom rules
    [cyan][3][/cyan]  Find duplicates     [cyan][6][/cyan]  AI classify

    [cyan][7][/cyan]  Watch mode          [cyan][8][/cyan]  Undo last operation

    [cyan][S][/cyan]  Schedule tasks      [cyan][H][/cyan]  Help (this screen)
    [cyan][Q][/cyan]  Quit

  [bold magenta]Navigation[/bold magenta]

    Arrow keys  =  Move between options
    Enter       =  Confirm selection
    Space       =  Toggle checkboxes
    Ctrl+C      =  Cancel / Go back

  [bold magenta]Cloud Drive Detection[/bold magenta]

    On startup, the TUI detects cloud-synced folders (OneDrive,
    Dropbox, Google Drive) and asks whether to skip them.
    [yellow]Skipping prevents sync conflicts.[/yellow]

  [bold magenta]Panels[/bold magenta]

    [bold]Main Menu[/bold] (left)   —  Available actions
    [bold]Quick Stats[/bold] (top-right)  —  File counts in common dirs
    [bold]Activity Log[/bold] (bottom-right) —  History of operations
"""


def get_config_guide() -> str:
    """Configuration file reference."""
    return """
[bold cyan]Configuration Guide[/bold cyan]

  Config file: [bold]~/.prism-organizer/config.yaml[/bold]
  Auto-created on first run.  Edit to customize.

  [bold magenta]Key Settings[/bold magenta]

    [bold]categories[/bold]       File extensions grouped by category
                       Add custom extensions or new categories.

    [bold]junk_patterns[/bold]    Glob patterns for auto-cleanup
                       e.g., '*.tmp', '~$*', 'Thumbs.db'

    [bold]duplicates[/bold]       Duplicate detection settings
                       method: hash, keep: oldest/newest
                       min_size: '1MB', perceptual_threshold: 5

    [bold]cloud_drives[/bold]     Auto-detect and skip cloud folders
                       auto_detect: true/false

    [bold]ai[/bold]               AI classification & renaming
                       enabled: true, provider: openai|ollama|lmstudio
                       model: 'gpt-4o-mini', features: {classify_unknown: true}

    [bold]watcher[/bold]          Real-time directory monitoring
                       cooldown_seconds: 10, min_file_age_seconds: 5

    [bold]custom_rules[/bold]     Your own file organization rules
                       Match by extension, name, size, age.
                       Actions: move, copy, rename, delete, archive.

  [bold magenta]Example Custom Rule[/bold magenta]

    custom_rules:
      - name: "Archive old installers"
        match:
          extension: [.exe, .msi]
          size_gt: "100MB"
          older_than: "30d"
        action: move
        destination: "~/Archive/Installers/"
"""


def get_safety_guide() -> str:
    """Safety features documentation."""
    return """
[bold cyan]Safety & Recovery Guide[/bold cyan]

  Prism Organizer is designed to be safe-first:

  [bold green]Dry-Run Previews[/bold green]
    Every destructive command shows a preview first.
    No files are changed until you confirm.

  [bold green]Backup Before Delete[/bold green]
    "Deleted" files are moved to [bold].prism-organizer_backup/[/bold]
    inside the target directory.  They are NOT sent to the
    Windows Recycle Bin — they stay in the backup folder.

  [bold green]Undo Support[/bold green]
    Every operation is logged.  Reverse the last action:
      prism-organizer undo

    List recent operations:
      prism-organizer undo --list

  [bold green]Cloud Drive Protection[/bold green]
    OneDrive, Dropbox, Google Drive, etc. are auto-detected.
    The app asks before organizing anything that could cause
    sync conflicts.

  [bold green]Operation Logs[/bold green]
    All actions are recorded in [bold]~/.prism-organizer/logs/[/bold]
    Each log file contains the exact files moved, deleted, or
    renamed — including original and new locations.

  [bold yellow]To permanently delete files:[/bold yellow]
    Delete the .prism-organizer_backup/ folder manually.
"""


def get_ai_guide() -> str:
    """AI integration setup guide."""
    return """
[bold cyan]AI Integration Setup[/bold cyan]

  Prism Organizer supports AI classification of unknown files.
  It uses any OpenAI-compatible API — cloud or local.

  [bold magenta]Enable AI[/bold magenta]

    Edit [bold]~/.prism-organizer/config.yaml[/bold]:
      ai:
        enabled: true
        provider: "openai"       # or "ollama", "lmstudio"
        model: "gpt-4o-mini"     # or "llama3.2", "phi-4", etc.
        features:
          classify_unknown: true  # suggest categories
          smart_rename: false     # AI-powered renaming
        min_confidence: 0.7       # only act above this

  [bold magenta]Using OpenAI (Cloud)[/bold magenta]

    Set your API key:
      ai:
        api_key: "sk-..."        # or set OPENAI_API_KEY env var

  [bold magenta]Using Ollama (Local, Free)[/bold magenta]

    1. Install Ollama:  https://ollama.com
    2. Pull a model:     ollama pull llama3.2
    3. Configure:
         ai:
           enabled: true
           provider: "ollama"
           model: "llama3.2"

    [green]No API key needed — everything runs on your machine.[/green]

  [bold magenta]Using LM Studio (Local, Free)[/bold magenta]

    1. Install LM Studio:  https://lmstudio.ai
    2. Load a model in the UI
    3. Start the local server
    4. Configure:
         ai:
           enabled: true
           provider: "lmstudio"
           model: "local-model"

  [bold magenta]Security[/bold magenta]

    Only filenames, extensions, and short text previews (~500 chars)
    are sent to the AI.  No files are ever uploaded.
    With local models, nothing leaves your machine.
"""


def build_help(topic: str = "") -> str:
    """Build the full help text.  Pass a topic name for a single section.

    Available topics: quickstart, commands, tui, config, safety, ai
    """
    sections = {
        "quickstart": ("Quick Start", get_quick_start),
        "commands": ("Command Reference", get_command_reference),
        "tui": ("TUI Guide", get_tui_guide),
        "config": ("Configuration", get_config_guide),
        "safety": ("Safety & Recovery", get_safety_guide),
        "ai": ("AI Setup", get_ai_guide),
    }

    if topic and topic in sections:
        title, fn = sections[topic]
        return f"[bold cyan]══ {title} ══[/bold cyan]\n" + fn()

    # Full help
    lines = ["", "[bold magenta]══ Prism Organizer v1.2.14 — Help ══[/bold magenta]", ""]
    lines.append(get_quick_start())
    lines.append(get_command_reference())
    lines.append(get_tui_guide())
    lines.append(get_config_guide())
    lines.append(get_safety_guide())
    lines.append("")
    lines.append(
        "[bold magenta]For a specific topic:[/bold magenta] "
        "prism-organizer help --topic [quickstart|commands|tui|config|safety|ai]"
    )
    lines.append("")
    return "\n".join(lines)
