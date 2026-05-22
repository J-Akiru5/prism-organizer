"""Command-line interface for Prism Organizer.

Defines all subcommands and orchestrates the app.

Usage:
    prism-organizer scan <path>          - Analyze directory
    prism-organizer sort <path>          - Sort files by type (default) or date
    prism-organizer dupes <path>         - Find duplicate files
    prism-organizer clean <path>         - Clean junk/temp files
    prism-organizer rules <path>         - Apply custom rules
    prism-organizer undo                 - Undo last operation
    prism-organizer ai-classify <path>   - AI-powered category suggestions
    prism-organizer watch <path>         - Watch directory for changes
    prism-organizer schedule [add|list|remove]  - Manage scheduled tasks
    prism-organizer tui                  - Interactive TUI dashboard
"""

import argparse
import sys
from pathlib import Path
from typing import Any, Optional, Set

from colorama import init as colorama_init

from prism_organizer import __version__
from prism_organizer.config import Config
from prism_organizer.scanner import Scanner
from prism_organizer.sorter import Sorter
from prism_organizer.duplicates import DuplicateDetector
from prism_organizer.cleaner import Cleaner
from prism_organizer.rules import RuleEngine
from prism_organizer.cloud_drives import CloudDriveDetector
from prism_organizer.preview import Preview
from prism_organizer.executor import Executor
from prism_organizer.undo import UndoManager
from prism_organizer.ai import AIEngine
from prism_organizer.watcher import DirectoryWatcher, TaskScheduler
from prism_organizer.tui import run_tui
from prism_organizer.help import build_help
from prism_organizer.display import (
    display_header, display_table, display_info, display_warning,
    display_success, display_confirm,
    display_splash, display_exit_banner, init_display,
)
from prism_organizer.utils import (
    expand_path, print_header, print_success, print_error,
    print_warning, print_info, APP_NAME,
)


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser with all subcommands.

    Returns:
        argparse.ArgumentParser: Fully configured parser with subcommands
        for scan, sort, dupes, clean, rules, and undo.
    """
    parser = argparse.ArgumentParser(
        prog="prism-organizer",
        description=f"{APP_NAME} - A portable CLI tool for scanning, analyzing, and organizing files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  prism-organizer scan ~/Downloads
  prism-organizer sort ~/Downloads --by type
  prism-organizer sort ~/Downloads --by date
  prism-organizer dupes ~/Downloads
  prism-organizer dupes ~/Downloads --clean --perceptual
  prism-organizer clean ~/Downloads
  prism-organizer rules ~/Downloads
  prism-organizer undo
  prism-organizer ai-classify ~/Downloads
  prism-organizer ai-classify ~/Downloads --rename
  prism-organizer watch ~/Downloads
  prism-organizer schedule add ~/Downloads --command sort --interval daily
  prism-organizer schedule list
""",
    )
    parser.add_argument(
        "--version", action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--config", type=str, default=None,
        help="Path to custom config file",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--workers", "-w", type=int, default=None,
        help="Number of worker threads (default: CPU count)",
    )
    parser.add_argument(
        "--no-interactive", action="store_true",
        help="Disable arrow-key prompts, use plain text input",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # scan
    scan_parser = subparsers.add_parser("scan", help="Analyze a directory and show report")
    scan_parser.add_argument("path", help="Directory to scan")
    scan_parser.add_argument("--recursive", action=argparse.BooleanOptionalAction, default=True)

    # sort
    sort_parser = subparsers.add_parser("sort", help="Sort files into organized folders")
    sort_parser.add_argument("path", help="Directory to sort")
    sort_parser.add_argument("--by", choices=["type", "date"], default="type", help="Sort method (default: type)")
    sort_parser.add_argument("--recursive", action=argparse.BooleanOptionalAction, default=True)
    sort_parser.add_argument("--dry-run", action="store_true", default=True, help="Preview only (default)")
    sort_parser.add_argument("--confirm", action="store_true", help="Skip preview, execute directly")

    # dupes
    dupes_parser = subparsers.add_parser("dupes", help="Find duplicate files")
    dupes_parser.add_argument("path", help="Directory to check")
    dupes_parser.add_argument("--clean", action="store_true", help="Prompt to remove duplicates")
    dupes_parser.add_argument("--recursive", action=argparse.BooleanOptionalAction, default=True)
    dupes_parser.add_argument("--perceptual", action="store_true", help="Also find visually similar images (requires imagehash)")

    # clean
    clean_parser = subparsers.add_parser("clean", help="Clean junk/temp files")
    clean_parser.add_argument("path", help="Directory to clean")
    clean_parser.add_argument("--recursive", action=argparse.BooleanOptionalAction, default=True)
    clean_parser.add_argument("--dry-run", action="store_true", default=True, help="Preview only (default)")
    clean_parser.add_argument("--confirm", action="store_true", help="Skip preview, execute directly")
    clean_parser.add_argument("--review-folder", type=str, default=None,
                              help="Move items to this folder instead of backup (for manual review)")

    # rules
    rules_parser = subparsers.add_parser("rules", help="Apply custom rules from config")
    rules_parser.add_argument("path", help="Directory to process")
    rules_parser.add_argument("--recursive", action=argparse.BooleanOptionalAction, default=True)
    rules_parser.add_argument("--dry-run", action="store_true", default=True, help="Preview only (default)")
    rules_parser.add_argument("--confirm", action="store_true", help="Skip preview, execute directly")

    # undo
    undo_parser = subparsers.add_parser("undo", help="Undo last operation")
    undo_parser.add_argument("--list", action="store_true", help="List recent operations")

    # ai-classify
    ai_parser = subparsers.add_parser("ai-classify", help="Use AI to suggest categories for unknown files")
    ai_parser.add_argument("path", help="Directory to analyze")
    ai_parser.add_argument("--recursive", action=argparse.BooleanOptionalAction, default=True)
    ai_parser.add_argument("--rename", action="store_true", help="Also suggest smart renames")

    # ai-setup
    subparsers.add_parser("ai-setup", help="Interactive wizard to configure AI features")

    # watch
    watch_parser = subparsers.add_parser("watch", help="Watch directories for changes and auto-organize")
    watch_parser.add_argument("path", help="Directory to watch")
    watch_parser.add_argument("--action", choices=["sort", "clean", "all"], default="sort",
                              help="Action to trigger (default: sort)")

    # schedule
    sched_parser = subparsers.add_parser("schedule", help="Manage scheduled tasks (Windows Task Scheduler)")
    sched_sub = sched_parser.add_subparsers(dest="schedule_cmd")

    sched_add = sched_sub.add_parser("add", help="Add a scheduled task")
    sched_add.add_argument("path", help="Directory to operate on")
    sched_add.add_argument("--command", choices=["scan", "sort", "clean", "rules"],
                           default="sort", help="Command to run")
    sched_add.add_argument("--interval", choices=["daily", "weekly", "hourly"],
                           default="daily", help="Schedule interval")
    sched_add.add_argument("--at", default="09:00", help="Time to run (HH:MM, 24h)")

    sched_sub.add_parser("list", help="List scheduled tasks")
    sched_sub.add_parser("remove", help="Remove a scheduled task")

    # tui
    subparsers.add_parser("tui", help="Launch interactive TUI dashboard")

    # help
    help_parser = subparsers.add_parser("help", help="Show comprehensive help and guides")
    help_parser.add_argument("--topic", choices=["quickstart", "commands", "tui", "config", "safety", "ai"],
                             help="Specific help topic")

    return parser


def _detect_cloud_drives(config: Config) -> Set[Path]:
    """Detect cloud-synced directories and prompt the user about them.

    Uses interactive arrow-key menus when questionary is installed,
    falls back to the cloud_drives.prompt_user text interface.
    """
    detector = CloudDriveDetector(config)
    detected = detector.detect()
    if detected:
        try:
            from prism_organizer.interactive import (
                interactive_cloud_drive_selection,
            )
            skip_list, _ = interactive_cloud_drive_selection(detected)
            return {d.path for d in skip_list}
        except Exception:
            return detector.prompt_user(detected)
    return set()


def cmd_scan(args: argparse.Namespace, config: Config) -> None:
    """Execute the scan command.

    Scans the target directory and prints a detailed report of its
    contents, including file type breakdown, size distribution, and
    age analysis.

    Args:
        args: Parsed command-line arguments containing path and options.
        config: Application configuration instance.
    """
    skip_dirs = _detect_cloud_drives(config)

    scanner = Scanner(config)
    result = scanner.scan(
        target=args.path,
        recursive=args.recursive,
        skip_dirs=skip_dirs,
        workers=args.workers,
    )
    scanner.print_report(result, verbose=args.verbose)


def cmd_sort(args: argparse.Namespace, config: Config) -> None:
    """Execute the sort command.

    Plans and optionally executes file sorting by type or date. Only
    scans top-level files for safety. Shows a dry-run preview by
    default; use --confirm to execute immediately.

    Args:
        args: Parsed command-line arguments containing path, sort method,
              and execution flags.
        config: Application configuration instance.
    """
    skip_dirs = _detect_cloud_drives(config)

    scanner = Scanner(config)
    scan_result = scanner.scan(
        target=args.path,
        recursive=False,  # Sort only scans top-level for safety
        skip_dirs=skip_dirs,
        workers=args.workers,
    )

    sorter = Sorter(config)
    if args.by == "date":
        plan = sorter.plan_sort_by_date(scan_result, skip_dirs=skip_dirs)
    else:
        plan = sorter.plan_sort_by_type(scan_result, skip_dirs=skip_dirs)

    if plan.total_files == 0:
        print_info("No files to sort.")
        return

    preview = Preview()
    if args.confirm or preview.show_sort_preview(plan):
        executor = Executor(config)
        executor.execute_sort(plan)
    else:
        print_info("Operation cancelled.")


def cmd_dupes(args: argparse.Namespace, config: Config) -> None:
    """Execute the dupes command.

    Finds duplicate files using content hashing and displays a report.
    When --clean is specified, prompts the user to select which
    duplicates to remove.  When --perceptual is specified, also finds
    visually similar (but not byte-identical) images.

    Args:
        args: Parsed command-line arguments containing path and options.
        config: Application configuration instance.
    """
    skip_dirs = _detect_cloud_drives(config)

    scanner = Scanner(config)
    scan_result = scanner.scan(
        target=args.path,
        recursive=args.recursive,
        skip_dirs=skip_dirs,
        workers=args.workers,
    )

    detector = DuplicateDetector(config)
    result = detector.find_duplicates(scan_result, workers=args.workers)

    # Perceptual (near-duplicate image) detection
    if args.perceptual:
        perceptual_config = config.duplicates_config
        threshold = perceptual_config.get("perceptual_threshold", 5)
        result.perceptual_groups = detector.find_perceptual_duplicates(
            scan_result, threshold=threshold, workers=args.workers,
        )

    detector.print_report(result)

    if args.clean and result.has_duplicates:
        preview = Preview()
        if preview.show_duplicates_preview(result):
            executor = Executor(config)
            executor.execute_duplicate_cleanup(result, expand_path(args.path))


def cmd_clean(args: argparse.Namespace, config: Config) -> None:
    """Execute the clean command.

    Identifies junk and temporary files (e.g., Thumbs.db, .DS_Store,
    __pycache__) and plans their removal. Shows a dry-run preview by
    default; use --confirm to execute immediately.

    Args:
        args: Parsed command-line arguments containing path and options.
        config: Application configuration instance.
    """
    skip_dirs = _detect_cloud_drives(config)

    scanner = Scanner(config)
    scan_result = scanner.scan(
        target=args.path,
        recursive=args.recursive,
        skip_dirs=skip_dirs,
        workers=args.workers,
    )

    cleaner = Cleaner(config)
    plan = cleaner.plan_cleanup(scan_result)

    if plan.total_items == 0:
        print_success("Nothing to clean!")
        return

    preview = Preview()
    if args.confirm or preview.show_cleanup_preview(plan):
        review = expand_path(args.review_folder) if args.review_folder else None
        executor = Executor(config)
        executor.execute_cleanup(plan, expand_path(args.path), review_folder=review)
    else:
        print_info("Operation cancelled.")


def cmd_rules(args: argparse.Namespace, config: Config) -> None:
    """Execute the rules command.

    Applies user-defined rules from the configuration file. Rules can
    match files by extension, name pattern, or size and move/rename
    them accordingly. Shows a dry-run preview by default.

    Args:
        args: Parsed command-line arguments containing path and options.
        config: Application configuration instance.
    """
    if not config.custom_rules:
        print_warning("No custom rules defined in config.")
        print_info(f"Add rules to your config file: {config._config_path}")
        return

    skip_dirs = _detect_cloud_drives(config)

    scanner = Scanner(config)
    scan_result = scanner.scan(
        target=args.path,
        recursive=args.recursive,
        skip_dirs=skip_dirs,
        workers=args.workers,
    )

    engine = RuleEngine(config)
    plan = engine.evaluate(scan_result)

    if plan.total_matches == 0:
        print_info("No files matched any rules.")
        return

    preview = Preview()
    if args.confirm or preview.show_rules_preview(plan):
        executor = Executor(config)
        executor.execute_rules(plan, expand_path(args.path))
    else:
        print_info("Operation cancelled.")


def cmd_help(args: argparse.Namespace, config: Config) -> None:
    """Execute the help command.

    Displays comprehensive documentation including quick-start guide,
    command reference, TUI navigation, configuration, and safety.
    """
    import re
    import sys
    topic = getattr(args, "topic", None) or ""
    text = build_help(topic)
    # Strip Rich markup tags
    plain = re.sub(r'\[/?[a-z ]+\]', '', text)
    # Strip emoji and non-ASCII for safe Windows console output
    plain = plain.encode("ascii", errors="ignore").decode("ascii")
    # Write directly to stdout buffer (UTF-8)
    try:
        sys.stdout.buffer.write(plain.encode("utf-8") + b"\n")
    except Exception:
        sys.stdout.write(plain + "\n")


def cmd_undo(args: argparse.Namespace, config: Config) -> None:
    """Execute the undo command.

    Reverts the most recent file operation, or lists recent operations
    when --list is specified. Undo data is stored in the log directory
    and tracks every file move, rename, and delete.

    Args:
        args: Parsed command-line arguments containing undo options.
        config: Application configuration instance.
    """
    manager = UndoManager()

    if hasattr(args, 'list') and args.list:
        operations = manager.list_operations()
        if not operations:
            print_info("No operations to undo.")
            return

        print_header("RECENT OPERATIONS")
        for i, op in enumerate(operations, 1):
            cmd = op.get("command", "unknown")
            ts = op.get("timestamp", "unknown")
            target = op.get("target_dir", "unknown")
            count = len(op.get("operations", []))
            print(f"  {i}. [{ts}] {cmd} on {target} ({count} operations)")
        return

    manager.undo_last()


def cmd_ai_classify(args: argparse.Namespace, config: Config) -> None:
    """Execute the ai-classify command.

    Scans the target directory and uses AI to suggest categories for
    files with unknown extensions.  With --rename, also suggests
    descriptive filenames for auto-generated names.
    """
    if not config.ai_config.get("enabled", False):
        print_warning(
            "AI features are disabled.  Enable them in "
            f"{config._config_path} under the 'ai:' section."
        )
        return

    engine = AIEngine(config)

    if not engine.provider.check_available():
        print_warning(
            "The 'openai' package is required for AI features.  "
            "Install with: pip install openai"
        )
        return

    skip_dirs = _detect_cloud_drives(config)

    scanner = Scanner(config)
    scan_result = scanner.scan(
        target=args.path,
        recursive=args.recursive,
        skip_dirs=skip_dirs,
        workers=args.workers,
    )

    # Classify unknown files
    if engine.provider.classify_enabled:
        misc_files = [fi for fi in scan_result.files if fi.category == "Misc"]
        if misc_files:
            print_info(f"AI classifying {len(misc_files)} unknown files...")
            classifications = engine.classify_unknown(scan_result.files)

            high_confidence = [
                c for c in classifications
                if c.confidence >= engine.provider.min_confidence
                and c.suggested_category != c.file_info.category
            ]
            low_confidence = [
                c for c in classifications
                if c not in high_confidence
            ]

            if high_confidence:
                display_header("AI CLASSIFICATION SUGGESTIONS")

                rows = []
                for c in high_confidence:
                    rows.append((
                        c.file_info.name,
                        f"{c.file_info.category} -> {c.suggested_category}",
                        f"{c.confidence:.0%}",
                        c.reasoning[:60],
                    ))

                display_table(
                    title=f"Suggested Reclassifications "
                          f"(confidence >= {engine.provider.min_confidence:.0%})",
                    columns=[
                        {"header": "File", "width": 35},
                        {"header": "Suggestion", "width": 30},
                        {"header": "Confidence", "justify": "right", "width": 12},
                        {"header": "Reasoning", "width": 40},
                    ],
                    rows=rows,
                )

                if display_confirm("Apply these reclassifications?"):
                    executor = Executor(config)
                    plan = _build_classification_plan(
                        high_confidence, scan_result.target_dir,
                    )
                    executor.execute_rules(plan, expand_path(args.path))

            if low_confidence:
                display_info(
                    f"{len(low_confidence)} files had low-confidence or "
                    f"unchanged suggestions (skipped)"
                )
        else:
            display_success("No unknown files to classify.")

    # Smart rename
    if args.rename and engine.provider.rename_enabled:
        renames = engine.suggest_renames(scan_result.files)

        if renames:
            display_header("AI RENAME SUGGESTIONS")
            rows = []
            for r in renames:
                rows.append((
                    r.file_info.name,
                    r.new_name + r.file_info.extension,
                    r.reasoning[:60],
                ))
            display_table(
                title="Suggested Renames",
                columns=[
                    {"header": "Current", "width": 35},
                    {"header": "Suggested", "width": 35},
                    {"header": "Reasoning", "width": 40},
                ],
                rows=rows,
            )

            if display_confirm("Apply these renames?"):
                executor = Executor(config)
                plan = _build_rename_plan(renames)
                executor.execute_rules(plan, expand_path(args.path))
        else:
            display_success("No files to rename.")


def _build_classification_plan(
    classifications: list,
    target_dir: Path,
) -> Any:
    """Build a temporary RulePlan from AI classifications."""
    from prism_organizer.rules import RulePlan, RuleMatch
    from prism_organizer.utils import safe_filename

    plan = RulePlan()
    for c in classifications:
        dest_dir = target_dir / c.suggested_category
        dest = safe_filename(dest_dir, c.file_info.name)
        plan.matches.append(RuleMatch(
            file_info=c.file_info,
            rule_name="AI Classification",
            action="move",
            destination=dest,
        ))
    return plan


def _build_rename_plan(renames: list) -> Any:
    """Build a temporary RulePlan from AI rename suggestions."""
    from prism_organizer.rules import RulePlan, RuleMatch

    plan = RulePlan()
    for r in renames:
        new_name = r.new_name + r.file_info.extension
        plan.matches.append(RuleMatch(
            file_info=r.file_info,
            rule_name="AI Rename",
            action="rename",
            new_name=new_name,
        ))
    return plan


def cmd_watch(args: argparse.Namespace, config: Config) -> None:
    """Execute the watch command.

    Monitors a directory in real-time and triggers file organization
    when new files appear.

    Args:
        args: Parsed command-line arguments.
        config: Application configuration instance.
    """
    actions = ["sort"] if args.action == "sort" else (
        ["clean"] if args.action == "clean" else ["sort", "clean"]
    )

    def _on_change(watch_path: Path, act: List[str]) -> None:
        print_info(f"Triggering {'/'.join(act)} on {watch_path}")
        from prism_organizer.scanner import Scanner
        from prism_organizer.sorter import Sorter
        from prism_organizer.cleaner import Cleaner
        from prism_organizer.executor import Executor
        from prism_organizer.preview import Preview

        scanner = Scanner(config)
        scan_result = scanner.scan(target=str(watch_path), recursive=False)

        if "sort" in act:
            sorter = Sorter(config)
            plan = sorter.plan_sort_by_type(scan_result)
            if plan.total_files > 0:
                executor = Executor(config)
                executor.execute_sort(plan)

        if "clean" in act:
            cleaner = Cleaner(config)
            plan = cleaner.plan_cleanup(scan_result)
            if plan.total_items > 0:
                preview = Preview()
                if preview.show_cleanup_preview(plan):
                    executor = Executor(config)
                    executor.execute_cleanup(plan, watch_path, review_folder=None)

    watcher = DirectoryWatcher(config)
    watcher.add_directory(args.path, actions=actions)
    watcher.set_callback(_on_change)
    watcher.start()


def cmd_schedule(args: argparse.Namespace, config: Config) -> None:
    """Execute the schedule command.

    Manages Windows Task Scheduler entries for periodic file
    organization.

    Args:
        args: Parsed command-line arguments.
        config: Application configuration instance.
    """
    sched = TaskScheduler()

    sub = args.schedule_cmd
    if sub == "add":
        sched.add_task(
            path=args.path,
            command=args.command,
            interval=args.interval,
            time_str=args.at,
        )
    elif sub == "list":
        tasks = sched.list_tasks()
        if not tasks:
            print_info("No scheduled tasks found.")
            return
        print_header("SCHEDULED TASKS")
        for t in tasks:
            print(f"  {t['name']}")
            print(f"    Next run: {t['next_run']} | Status: {t['status']}")
        print()
    elif sub == "remove":
        tasks = sched.list_tasks()
        if not tasks:
            print_info("No scheduled tasks to remove.")
            return
        print_header("SELECT TASK TO REMOVE")
        for i, t in enumerate(tasks, 1):
            print(f"  {i}. {t['name']}")
        print()
        try:
            choice = input("  Enter number (or Enter to cancel): ").strip()
        except (KeyboardInterrupt, EOFError):
            return
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(tasks):
                sched.remove_task(tasks[idx]["name"])
    else:
        print_info("Use: prism-organizer schedule [add|list|remove]")


def main() -> None:
    """Main entry point for the CLI.

    Initializes colorama for cross-platform colored output, parses
    command-line arguments, loads configuration, and dispatches to
    the appropriate command handler. Handles KeyboardInterrupt and
    common exceptions gracefully.
    """
    colorama_init(autoreset=True)
    init_display()

    parser = create_parser()
    args = parser.parse_args()

    # Boot: load config (protected — friendly error on failure)
    try:
        config = Config(config_path=args.config)
    except Exception as e:
        print_error(f"Startup error: {e}")
        sys.exit(1)

    # No subcommand → launch TUI dashboard
    if not args.command:
        try:
            display_splash()
            run_tui(config)
        except KeyboardInterrupt:
            print("\n")
            print_info("Goodbye!")
        except Exception as e:
            print_error(f"Startup error: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
        display_exit_banner()
        sys.exit(0)

    # Show splash for TUI mode
    if args.command == "tui":
        display_splash()

    # Set no-interactive mode if requested
    if getattr(args, "no_interactive", False):
        import os
        os.environ["PRISM_NO_INTERACTIVE"] = "1"

    # Dispatch to command handler
    commands = {
        "scan": cmd_scan,
        "sort": cmd_sort,
        "dupes": cmd_dupes,
        "clean": cmd_clean,
        "rules": cmd_rules,
        "undo": cmd_undo,
        "ai-classify": cmd_ai_classify,
        "ai-setup": lambda a, c: _cmd_ai_setup(c),
        "watch": cmd_watch,
        "schedule": cmd_schedule,
        "tui": lambda a, c: run_tui(c),
        "help": cmd_help,
    }

    handler = commands.get(args.command)
    if handler:
        try:
            handler(args, config)
            display_exit_banner()
        except KeyboardInterrupt:
            print("\n")
            print_info("Operation cancelled by user.")
            sys.exit(130)
        except FileNotFoundError as e:
            print_error(str(e))
            sys.exit(1)
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    else:
        parser.print_help()


def _cmd_ai_setup(config: Config) -> None:
    """Launch the interactive AI setup wizard."""
    from prism_organizer.ai_setup import run_ai_setup
    run_ai_setup(config)


if __name__ == "__main__":
    main()
