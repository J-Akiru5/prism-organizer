"""Interactive TUI dashboard for Prism Organizer.

Presents a persistent terminal dashboard with live panels for
navigation, status, and operation feedback.  All subcommands
are accessible through keyboard shortcuts.

Uses ``rich.live.Live`` for real-time panel updates.
"""

import time
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console, Group
from rich.panel import Panel
from rich.layout import Layout
from rich.align import Align
from rich.text import Text
from rich.table import Table
from rich.live import Live
from rich import box
from rich.style import Style

from prism_organizer import __version__
from prism_organizer.config import Config
from prism_organizer.scanner import Scanner, ScanResult
from prism_organizer.sorter import Sorter, SortPlan
from prism_organizer.duplicates import DuplicateDetector, DuplicateResult
from prism_organizer.cleaner import Cleaner, CleanupPlan
from prism_organizer.rules import RuleEngine, RulePlan
from prism_organizer.executor import Executor
from prism_organizer.undo import UndoManager
from prism_organizer.cloud_drives import CloudDriveDetector
from prism_organizer.preview import Preview
from prism_organizer.ai import AIEngine
from prism_organizer.watcher import DirectoryWatcher, TaskScheduler
from prism_organizer.utils import (
    expand_path, format_size, APP_NAME,
    print_info, print_success, print_error, print_warning,
)
from prism_organizer.display import (
    get_console, THEME, display_header, display_success, display_error,
    display_warning, display_info, display_table, display_category_table,
    display_top_files, display_findings, display_operation_summary,
    display_category_icon, display_key_value,
)
from prism_organizer.interactive import (
    interactive_confirm, interactive_select, interactive_text,
)

# ── Constants ─────────────────────────────────────────────────────────

MENU_ITEMS = [
    ("1", "scan",    "Scan directory",       "\U0001f50d"),
    ("2", "sort",    "Sort files",           "\U0001f4c1"),
    ("3", "dupes",   "Find duplicates",      "\U0001f50e"),
    ("4", "clean",   "Clean junk files",     "\U0001f9f9"),
    ("5", "rules",   "Apply custom rules",   "\U0001f4dd"),
    ("6", "ai",      "AI classify",          "\U0001f916"),
    ("7", "watch",   "Watch mode",           "\U0001f440"),
    ("8", "undo",    "Undo last operation",  "\u21a9\ufe0f"),
]
SECONDARY_ITEMS = [
    ("S", "schedule", "Schedule tasks", "\U0001f4c5"),
    ("H", "help",     "Help",           "\u2753"),
    ("Q", "quit",     "Quit",           "\U0001f6aa"),
]

LOG_LINES: List[str] = []
MAX_LOG_LINES = 20


def add_log(msg: str, level: str = "info") -> None:
    """Add a message to the persistent log panel."""
    ts = time.strftime("%H:%M:%S")
    color = {
        "info": THEME["muted"],
        "success": THEME["success"],
        "warning": THEME["warning"],
        "error": THEME["error"],
    }.get(level, THEME["muted"])
    icon = {"info": "\u2139", "success": "\u2713", "warning": "\u26a0", "error": "\u2717"}.get(level, "\u2139")
    LOG_LINES.insert(0, f"[{color}][{ts}] {icon} {msg}[/{color}]")
    if len(LOG_LINES) > MAX_LOG_LINES:
        LOG_LINES.pop()


# ── Layout builders ───────────────────────────────────────────────────


def _make_banner() -> Panel:
    """Build the top banner panel."""
    title = Text(
        f" \U0001f52e  Prism Organizer v{__version__}",
        style=f"bold {THEME['accent']}",
    )
    subtitle = Text(
        "scan  |  sort  |  dupes  |  clean  |  rules  |  ai  |  undo",
        style=THEME["muted"],
    )
    return Panel(
        Align.center(Group(title, subtitle), vertical="middle"),
        box=box.DOUBLE,
        border_style=THEME["primary"],
    )


def _make_menu() -> Panel:
    """Build the main menu panel."""
    lines = []
    for key, cmd, desc, icon in MENU_ITEMS:
        lines.append(
            f"[bold {THEME['primary']}]{icon} [{key}][/bold {THEME['primary']}]  "
            f"[{THEME['info']}]{desc:<24}[/{THEME['info']}]"
        )
    lines.append("")
    sec = "  ".join(
        f"[bold {THEME['primary']}][{k}][/bold {THEME['primary']}] "
        f"[{THEME['muted']}]{desc}[/{THEME['muted']}]"
        for k, _, desc, _ in SECONDARY_ITEMS
    )
    lines.append(f"  {sec}")
    return Panel(
        "\n".join(lines),
        title=f"[bold {THEME['primary']}]\U0001f4cb  Main Menu",
        border_style=THEME["primary"],
        padding=(1, 2),
    )


def _make_log_panel() -> Panel:
    """Build the log/history panel."""
    if not LOG_LINES:
        content = f"  [{THEME['muted']}]No operations yet.  Use the menu to begin.{os.linesep}"
    else:
        content = os.linesep.join(LOG_LINES[:MAX_LOG_LINES])
    return Panel(
        content,
        title=f"[bold {THEME['primary']}]\U0001f4dc  Activity Log",
        border_style=THEME["border"],
        padding=(1, 1),
    )


def _make_stats_panel(config: Config) -> Panel:
    """Build a quick-stats panel from common directories."""
    lines = []
    for p_str in config.default_paths[:4]:
        p = expand_path(p_str)
        if p.exists():
            try:
                count = sum(1 for _ in p.iterdir() if _.is_file())
                lines.append(
                    f"  [{THEME['info']}]{p.name}:[/{THEME['info']}]  "
                    f"[bold {THEME['primary']}]{count}[/bold {THEME['primary']}]"
                    f"  [{THEME['muted']}]files"
                )
            except (OSError, PermissionError):
                pass
    if not lines:
        lines.append(f"  [{THEME['muted']}]No defaults set.{os.linesep}")
    return Panel(
        os.linesep.join(lines),
        title=f"[bold {THEME['primary']}]\U0001f4ca  Quick Stats",
        border_style=THEME["border"],
        padding=(1, 2),
    )


def _make_help_panel() -> Panel:
    """Build the help/legend panel."""
    help_text = (
        "\n".join(
            f"  [{THEME['primary']}][{k}][/{THEME['primary']}] "
            f"[{THEME['muted']}]{desc}"
            for k, _, desc, _ in MENU_ITEMS + SECONDARY_ITEMS
        )
        + f"\n\n  [{THEME['muted']}]Enter a key and press Enter to select"
    )
    return Panel(
        help_text,
        title=f"[bold {THEME['primary']}]\u2753  Keyboard Shortcuts",
        border_style=THEME["border"],
        padding=(1, 1),
    )


# ── Action state ──────────────────────────────────────────────────────

_current_state: Dict[str, Any] = {}


def _set_state(**kwargs) -> None:
    _current_state.update(kwargs)


def _clear_state() -> None:
    _current_state.clear()


# ── Menu layout ───────────────────────────────────────────────────────


def _build_layout(config: Config, active: str = "") -> Layout:
    """Construct the full TUI layout.

    Layout: top banner, middle (menu | stats), bottom (log | help).
    """
    layout = Layout()
    layout.split(
        Layout(name="banner", size=5),
        Layout(name="main", ratio=1),
    )
    layout["main"].split_row(
        Layout(name="menu", ratio=2),
        Layout(name="right", ratio=1),
    )
    layout["right"].split(
        Layout(name="stats", ratio=1),
        Layout(name="log", ratio=2),
    )

    layout["banner"].update(_make_banner())
    layout["menu"].update(_make_menu())
    layout["stats"].update(_make_stats_panel(config))
    layout["log"].update(_make_log_panel())

    return layout


# ── Action handlers ───────────────────────────────────────────────────


def _get_path(config: Config) -> Optional[Path]:
    """Prompt user for a directory path."""
    paths = config.default_paths
    choices = [expand_path(p) for p in paths if expand_path(p).exists()]
    choices_str = [str(c) for c in choices]
    choices_str.append("Custom path...")

    sel = interactive_select(
        "Select a directory to work on:",
        choices=choices_str,
        format_fn=lambda x: f"\U0001f4c1  {x}",
    )
    if sel == "Custom path...":
        custom = interactive_text(
            "Enter the directory path:",
            default=str(Path.home()),
        )
        if not custom:
            return None
        p = expand_path(custom)
        if not p.exists():
            display_error(f"Directory not found: {p}")
            add_log(f"Invalid path: {p}", "error")
            return None
        return p
    elif sel:
        return Path(sel)
    return None


def _action_scan(config: Config) -> bool:
    """Run scan action and display results."""
    target = _get_path(config)
    if not target:
        return False

    add_log(f"Scanning {target}...", "info")
    scanner = Scanner(config)
    result = scanner.scan(target=str(target))
    scanner.print_report(result, verbose=True)
    add_log(
        f"Scanned {target.name}: {result.total_files} files, "
        f"{format_size(result.total_size)}",
        "success",
    )
    return True


def _action_sort(config: Config) -> bool:
    """Run sort action with preview and confirm."""
    target = _get_path(config)
    if not target:
        return False

    scanner = Scanner(config)
    scan_result = scanner.scan(target=str(target), recursive=False)

    sort_by = interactive_select(
        "Sort method:",
        choices=["type", "date"],
        default="type",
        format_fn=lambda x: f"{'📁' if x == 'type' else '📅'}  Sort by {x}",
    )
    if not sort_by:
        return False

    sorter = Sorter(config)
    if sort_by == "date":
        plan = sorter.plan_sort_by_date(scan_result)
    else:
        plan = sorter.plan_sort_by_type(scan_result)

    if plan.total_files == 0:
        display_info("No files to sort.")
        add_log(f"No files to sort in {target.name}", "info")
        return False

    preview = Preview()
    if preview.show_sort_preview(plan):
        executor = Executor(config)
        executor.execute_sort(plan)
        add_log(
            f"Sorted {plan.total_files} files in {target.name}",
            "success",
        )
    else:
        add_log("Sort cancelled", "info")
    return True


def _action_dupes(config: Config) -> bool:
    """Run duplicate detection action."""
    target = _get_path(config)
    if not target:
        return False

    scanner = Scanner(config)
    scan_result = scanner.scan(target=str(target))
    detector = DuplicateDetector(config)
    result = detector.find_duplicates(scan_result)

    # Ask about perceptual
    use_perceptual = interactive_confirm(
        "Also check for visually similar (near-duplicate) images?",
        default=False,
    )
    if use_perceptual:
        perceptual_config = config.duplicates_config
        threshold = perceptual_config.get("perceptual_threshold", 5)
        result.perceptual_groups = detector.find_perceptual_duplicates(
            scan_result, threshold=threshold,
        )

    detector.print_report(result)

    if result.has_duplicates:
        do_clean = interactive_confirm(
            "Remove duplicate files? (originals are backed up)",
            default=False,
        )
        if do_clean:
            preview = Preview()
            if preview.show_duplicates_preview(result):
                executor = Executor(config)
                executor.execute_duplicate_cleanup(result, target)
                add_log(
                    f"Removed {result.total_duplicates} duplicates from "
                    f"{target.name}",
                    "success",
                )
    else:
        add_log(f"No duplicates in {target.name}", "info")
    return True


def _action_clean(config: Config) -> bool:
    """Run cleanup action."""
    target = _get_path(config)
    if not target:
        return False

    scanner = Scanner(config)
    scan_result = scanner.scan(target=str(target))
    cleaner = Cleaner(config)
    plan = cleaner.plan_cleanup(scan_result)

    if plan.total_items == 0:
        display_success("Nothing to clean!")
        add_log(f"Nothing to clean in {target.name}", "success")
        return False

    preview = Preview()
    if preview.show_cleanup_preview(plan):
        executor = Executor(config)
        executor.execute_cleanup(plan, target)
        add_log(
            f"Cleaned {plan.total_items} items from {target.name}",
            "success",
        )
    else:
        add_log("Cleanup cancelled", "info")
    return True


def _action_rules(config: Config) -> bool:
    """Run custom rules action."""
    if not config.custom_rules:
        display_warning("No custom rules defined in config.")
        add_log("No custom rules configured", "warning")
        return False

    target = _get_path(config)
    if not target:
        return False

    scanner = Scanner(config)
    scan_result = scanner.scan(target=str(target))
    engine = RuleEngine(config)
    plan = engine.evaluate(scan_result)

    if plan.total_matches == 0:
        display_info("No files matched any rules.")
        add_log(
            f"No rule matches in {target.name}", "info"
        )
        return False

    preview = Preview()
    if preview.show_rules_preview(plan):
        executor = Executor(config)
        executor.execute_rules(plan, target)
        add_log(
            f"Applied {plan.total_matches} rule actions in "
            f"{target.name}",
            "success",
        )
    else:
        add_log("Rules cancelled", "info")
    return True


def _action_ai(config: Config) -> bool:
    """Run AI classification action."""
    if not config.ai_config.get("enabled", False):
        display_warning(
            "AI features are disabled.  Enable them in "
            f"{config._config_path} under the 'ai:' section."
        )
        add_log("AI disabled in config", "warning")
        return False

    engine = AIEngine(config)
    if not engine.provider.check_available():
        display_warning(
            "The 'openai' package is required for AI features.  "
            "Install with: pip install openai"
        )
        add_log("openai package not installed", "warning")
        return False

    target = _get_path(config)
    if not target:
        return False

    scanner = Scanner(config)
    scan_result = scanner.scan(target=str(target))

    misc_files = [fi for fi in scan_result.files if fi.category == "Misc"]
    if not misc_files:
        display_success("No unknown files to classify.")
        return False

    add_log(
        f"AI classifying {len(misc_files)} unknown files...",
        "info",
    )
    classifications = engine.classify_unknown(scan_result.files)

    high_confidence = [
        c for c in classifications
        if c.confidence >= engine.provider.min_confidence
        and c.suggested_category != c.file_info.category
    ]
    if high_confidence:
        display_header("AI Classification Suggestions")
        rows = [
            (
                c.file_info.name,
                f"{c.file_info.category} -> {c.suggested_category}",
                f"{c.confidence:.0%}",
                c.reasoning[:60],
            )
            for c in high_confidence
        ]
        display_table(
            title="Suggestions",
            columns=[
                {"header": "File", "width": 35},
                {"header": "Suggestion", "width": 30},
                {"header": "Conf", "justify": "right", "width": 8},
                {"header": "Reasoning", "width": 40},
            ],
            rows=rows,
        )
        if interactive_confirm("Apply these reclassifications?"):
            from prism_organizer.cli import _build_classification_plan
            executor = Executor(config)
            plan = _build_classification_plan(
                high_confidence, scan_result.target_dir,
            )
            executor.execute_rules(plan, target)
            add_log(
                f"AI reclassified {len(high_confidence)} files",
                "success",
            )
    else:
        display_info("No high-confidence suggestions.")
        add_log("AI: no high-confidence suggestions", "info")
    return True


def _action_watch(config: Config) -> bool:
    """Start watch mode action."""
    target = _get_path(config)
    if not target:
        return False

    action_sel = interactive_select(
        "Action on new files:",
        choices=["sort", "clean", "all"],
        default="sort",
        format_fn=lambda x: f"{'📁' if x == 'sort' else '🧹' if x == 'clean' else '📁+🧹'}  {x}",
    )
    if not action_sel:
        return False

    actions = (
        ["sort"] if action_sel == "sort"
        else ["clean"] if action_sel == "clean"
        else ["sort", "clean"]
    )

    def _on_change(wp: Path, act: List[str]) -> None:
        ts = time.strftime("%H:%M:%S")
        add_log(f"[{ts}] {len(act)} new files in {wp.name}", "info")

    watcher = DirectoryWatcher(config)
    watcher.add_directory(str(target), actions=actions)
    watcher.set_callback(_on_change)

    add_log(f"Watching {target.name} for changes...", "info")
    display_info(f"Watching {target} (Ctrl+C to stop)")
    display_info(f"Actions: {', '.join(actions)}")

    watcher.start()
    return True


def _action_undo(config: Config) -> bool:
    """Run undo action."""
    manager = UndoManager()
    operations = manager.list_operations(limit=5)

    if not operations:
        display_info("No operations to undo.")
        add_log("Nothing to undo", "info")
        return False

    display_header("Recent Operations")
    for i, op in enumerate(operations, 1):
        cmd = op.get("command", "unknown")
        ts = op.get("timestamp", "unknown")
        target = op.get("target_dir", "unknown")
        count = len(op.get("operations", []))
        print(f"  {i}. [{ts[:19]}] {cmd} — {target} ({count} ops)")

    if interactive_confirm("Undo the most recent operation?"):
        manager.undo_last()
        add_log("Undone last operation", "success")
    else:
        add_log("Undo cancelled", "info")
    return True


def _action_schedule(config: Config) -> bool:
    """Manage scheduled tasks."""
    sched = TaskScheduler()
    tasks = sched.list_tasks()

    action = interactive_select(
        "Schedule:",
        choices=["add", "list", "remove"],
        format_fn=lambda x: {
            "add": "\U0001f4c5  Add new task",
            "list": "\U0001f4cb  List tasks",
            "remove": "\U0001f5d1  Remove task",
        }.get(x, x),
    )
    if not action:
        return False

    if action == "list":
        if not tasks:
            display_info("No scheduled tasks found.")
            return False
        display_header("Scheduled Tasks")
        for t in tasks:
            print(f"  {t['name']}")
            print(f"    Next: {t['next_run']}  |  Status: {t['status']}")
        add_log(f"Listed {len(tasks)} scheduled tasks", "info")
        return True

    if action == "add":
        target = _get_path(config)
        if not target:
            return False
        cmd = interactive_select(
            "Command to schedule:",
            choices=["scan", "sort", "clean", "rules"],
            default="sort",
        )
        interval = interactive_select(
            "Interval:",
            choices=["daily", "weekly", "hourly"],
            default="daily",
        )
        time_str = interactive_text(
            "Start time (HH:MM, 24h):",
            default="09:00",
        )
        if not time_str:
            return False
        sched.add_task(str(target), cmd, interval, time_str)
        add_log(
            f"Scheduled {cmd} on {target.name} ({interval})",
            "success",
        )
        return True

    if action == "remove":
        if not tasks:
            display_info("No tasks to remove.")
            return False
        choices = [t["name"] for t in tasks]
        sel = interactive_select(
            "Remove task:",
            choices=choices,
        )
        if sel:
            sched.remove_task(sel)
            add_log(f"Removed task: {sel}", "success")
        return True

    return False


# ── Main TUI loop ─────────────────────────────────────────────────────


ACTION_MAP = {
    "1": ("scan", _action_scan),
    "2": ("sort", _action_sort),
    "3": ("dupes", _action_dupes),
    "4": ("clean", _action_clean),
    "5": ("rules", _action_rules),
    "6": ("ai", _action_ai),
    "7": ("watch", _action_watch),
    "8": ("undo", _action_undo),
    "s": ("schedule", _action_schedule),
}


def run_tui(config: Optional[Config] = None) -> None:
    """Launch the interactive TUI dashboard.

    Displays a persistent menu-driven interface with live panels.
    All subcommands are accessible through single-key shortcuts.

    Args:
        config: Optional pre-loaded configuration.  If None, a new
            Config instance is created.
    """
    if config is None:
        config = Config()

    # Detect cloud drives at launch
    detector = CloudDriveDetector(config)
    detected = detector.detect()
    if detected:
        from prism_organizer.interactive import interactive_cloud_drive_selection
        interactive_cloud_drive_selection(detected)

    console = get_console()
    layout = _build_layout(config)
    add_log("Prism Organizer ready.  Select an action.", "info")

    with Live(layout, console=console, refresh_per_second=4, screen=False):
        while True:
            layout = _build_layout(config)
            try:
                key = input(
                    f"\n  [{THEME['primary']}]{'─' * 25}[/{THEME['primary']}] "
                    f"[{THEME['accent']}]Enter choice[/{THEME['accent']}] "
                    f"[{THEME['primary']}]{'─' * 25}[/{THEME['primary']}]\n"
                    f"  > "
                ).strip().lower()
            except (KeyboardInterrupt, EOFError):
                print()
                add_log("Goodbye!", "info")
                break

            if key == "q":
                add_log("Goodbye!", "info")
                break

            if key == "h":
                console.clear()
                console.print(_make_help_panel())
                input("\n  Press Enter to return to menu...")
                console.clear()
                continue

            if key in ACTION_MAP:
                action_name, action_fn = ACTION_MAP[key]
                console.clear()
                try:
                    action_fn(config)
                except Exception as e:
                    display_error(f"Error: {e}")
                    add_log(f"Error in {action_name}: {e}", "error")
                input(
                    f"\n  [{THEME['muted']}]Press Enter to return to menu..."
                )
                console.clear()
            else:
                add_log(f"Unknown key: {key}", "warning")
