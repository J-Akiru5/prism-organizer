"""Command-line interface for Prism Organizer.

Defines all subcommands and orchestrates the app.

Usage:
    prism-organizer scan <path>          - Analyze directory
    prism-organizer sort <path>          - Sort files by type (default) or date
    prism-organizer dupes <path>         - Find duplicate files
    prism-organizer clean <path>         - Clean junk/temp files
    prism-organizer rules <path>         - Apply custom rules
    prism-organizer undo                 - Undo last operation
"""

import argparse
import sys
from pathlib import Path
from typing import Optional, Set

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
  prism-organizer dupes ~/Downloads --clean
  prism-organizer clean ~/Downloads
  prism-organizer rules ~/Downloads
  prism-organizer undo
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

    # clean
    clean_parser = subparsers.add_parser("clean", help="Clean junk/temp files")
    clean_parser.add_argument("path", help="Directory to clean")
    clean_parser.add_argument("--recursive", action=argparse.BooleanOptionalAction, default=True)
    clean_parser.add_argument("--dry-run", action="store_true", default=True, help="Preview only (default)")
    clean_parser.add_argument("--confirm", action="store_true", help="Skip preview, execute directly")

    # rules
    rules_parser = subparsers.add_parser("rules", help="Apply custom rules from config")
    rules_parser.add_argument("path", help="Directory to process")
    rules_parser.add_argument("--recursive", action=argparse.BooleanOptionalAction, default=True)
    rules_parser.add_argument("--dry-run", action="store_true", default=True, help="Preview only (default)")
    rules_parser.add_argument("--confirm", action="store_true", help="Skip preview, execute directly")

    # undo
    undo_parser = subparsers.add_parser("undo", help="Undo last operation")
    undo_parser.add_argument("--list", action="store_true", help="List recent operations")

    return parser


def _detect_cloud_drives(config: Config) -> Set[Path]:
    """Detect cloud-synced directories and prompt the user about them.

    Cloud drives (OneDrive, Dropbox, Google Drive, etc.) may cause issues
    during file organization. This function detects their presence and
    lets the user choose which ones to skip.

    Args:
        config: Application configuration instance.

    Returns:
        Set of Path objects representing cloud drive directories the user
        chose to skip, or an empty set if none were detected.
    """
    detector = CloudDriveDetector(config)
    detected = detector.detect()
    if detected:
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
        executor = Executor()
        executor.execute_sort(plan)
    else:
        print_info("Operation cancelled.")


def cmd_dupes(args: argparse.Namespace, config: Config) -> None:
    """Execute the dupes command.

    Finds duplicate files using content hashing and displays a report.
    When --clean is specified, prompts the user to select which
    duplicates to remove.

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
    )

    detector = DuplicateDetector(config)
    result = detector.find_duplicates(scan_result)

    detector.print_report(result)

    if args.clean and result.has_duplicates:
        preview = Preview()
        if preview.show_duplicates_preview(result):
            executor = Executor()
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
    )

    cleaner = Cleaner(config)
    plan = cleaner.plan_cleanup(scan_result)

    if plan.total_items == 0:
        print_success("Nothing to clean!")
        return

    preview = Preview()
    if args.confirm or preview.show_cleanup_preview(plan):
        executor = Executor()
        executor.execute_cleanup(plan, expand_path(args.path))
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
    )

    engine = RuleEngine(config)
    plan = engine.evaluate(scan_result)

    if plan.total_matches == 0:
        print_info("No files matched any rules.")
        return

    preview = Preview()
    if args.confirm or preview.show_rules_preview(plan):
        executor = Executor()
        executor.execute_rules(plan, expand_path(args.path))
    else:
        print_info("Operation cancelled.")


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


def main() -> None:
    """Main entry point for the CLI.

    Initializes colorama for cross-platform colored output, parses
    command-line arguments, loads configuration, and dispatches to
    the appropriate command handler. Handles KeyboardInterrupt and
    common exceptions gracefully.
    """
    colorama_init(autoreset=True)

    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Load config
    config = Config(config_path=args.config)

    # Dispatch to command handler
    commands = {
        "scan": cmd_scan,
        "sort": cmd_sort,
        "dupes": cmd_dupes,
        "clean": cmd_clean,
        "rules": cmd_rules,
        "undo": cmd_undo,
    }

    handler = commands.get(args.command)
    if handler:
        try:
            handler(args, config)
        except KeyboardInterrupt:
            print("\n")
            print_info("Operation cancelled by user.")
            sys.exit(130)
        except FileNotFoundError as e:
            print_error(str(e))
            sys.exit(1)
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
