import os
import re
import math
from pathlib import Path
from typing import Optional, Union

from colorama import Fore, Style, init as colorama_init

# Initialize colorama for Windows
colorama_init(autoreset=True)

# ── Constants ──────────────────────────────────────────────────────

APP_NAME = "Prism Organizer"
APP_DIR_NAME = ".prism-organizer"
CONFIG_FILENAME = "config.yaml"
BACKUP_DIR_NAME = ".prism-organizer_backup"
LOGS_DIR_NAME = "logs"


def get_app_dir() -> Path:
    """Get the application config directory (~/.prism-organizer/)."""
    return Path.home() / APP_DIR_NAME


def get_config_path() -> Path:
    """Get the default config file path."""
    return get_app_dir() / CONFIG_FILENAME


def get_logs_dir() -> Path:
    """Get the logs directory path."""
    logs = get_app_dir() / LOGS_DIR_NAME
    logs.mkdir(parents=True, exist_ok=True)
    return logs


def get_backup_dir(target_dir: Path) -> Path:
    """Get the backup directory for a given target directory."""
    backup = target_dir / BACKUP_DIR_NAME
    backup.mkdir(parents=True, exist_ok=True)
    return backup


# ── Size formatting ────────────────────────────────────────────────

def format_size(size_bytes: int) -> str:
    """Format bytes into human-readable size string.

    Examples:
        format_size(1024) -> '1.00 KB'
        format_size(1048576) -> '1.00 MB'
        format_size(0) -> '0 B'
    """
    if size_bytes <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = int(math.floor(math.log(size_bytes, 1024)))
    i = min(i, len(units) - 1)
    size = size_bytes / (1024 ** i)
    return f"{size:.2f} {units[i]}"


def parse_size(size_str: str) -> int:
    """Parse human-readable size string to bytes.

    Args:
        size_str: Size string like '50MB', '1.5GB', '1024', '100KB'

    Returns:
        Size in bytes.

    Raises:
        ValueError: If the size string is invalid.
    """
    size_str = size_str.strip().upper()
    multipliers = {
        'B': 1,
        'KB': 1024,
        'MB': 1024 ** 2,
        'GB': 1024 ** 3,
        'TB': 1024 ** 4,
    }
    match = re.match(r'^([\d.]+)\s*(B|KB|MB|GB|TB)?$', size_str)
    if not match:
        raise ValueError(f"Invalid size format: '{size_str}'. Use format like '50MB', '1.5GB'")

    value = float(match.group(1))
    unit = match.group(2) or 'B'
    return int(value * multipliers[unit])


def parse_age(age_str: str) -> int:
    """Parse age string to seconds.

    Args:
        age_str: Age string like '30d', '2w', '6h', '90m'
            d=days, w=weeks, h=hours, m=minutes

    Returns:
        Age in seconds.
    """
    age_str = age_str.strip().lower()
    multipliers = {
        'm': 60,
        'h': 3600,
        'd': 86400,
        'w': 604800,
    }
    match = re.match(r'^([\d.]+)\s*([mhdw])$', age_str)
    if not match:
        raise ValueError(f"Invalid age format: '{age_str}'. Use format like '30d', '2w', '6h'")

    value = float(match.group(1))
    unit = match.group(2)
    return int(value * multipliers[unit])


# ── UUID detection ─────────────────────────────────────────────────

UUID_PATTERN = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE
)


def is_uuid_filename(filename: str) -> bool:
    """Check if a filename (without extension) looks like a UUID."""
    stem = Path(filename).stem
    return bool(UUID_PATTERN.match(stem))


# ── Path helpers ───────────────────────────────────────────────────

def expand_path(path_str: str) -> Path:
    """Expand ~ and environment variables in a path string."""
    return Path(os.path.expandvars(os.path.expanduser(path_str))).resolve()


def safe_filename(dest_dir: Path, filename: str) -> Path:
    """Generate a safe filename that doesn't conflict with existing files.

    If 'photo.jpg' exists, returns 'photo_1.jpg', 'photo_2.jpg', etc.
    Uses underscores instead of parentheses for cleaner naming.
    """
    dest = dest_dir / filename
    if not dest.exists():
        return dest

    stem = Path(filename).stem
    suffix = Path(filename).suffix
    counter = 1
    while True:
        new_name = f"{stem}_{counter}{suffix}"
        dest = dest_dir / new_name
        if not dest.exists():
            return dest
        counter += 1


# ── Colored output helpers ─────────────────────────────────────────

def print_header(text: str) -> None:
    """Print a styled header."""
    width = 62
    print()
    print(f"{Fore.CYAN}{'═' * width}")
    print(f"{Fore.CYAN}  {text}")
    print(f"{Fore.CYAN}{'═' * width}{Style.RESET_ALL}")


def print_success(text: str) -> None:
    """Print a success message."""
    print(f"{Fore.GREEN}  ✓ {text}{Style.RESET_ALL}")


def print_warning(text: str) -> None:
    """Print a warning message."""
    print(f"{Fore.YELLOW}  ⚠ {text}{Style.RESET_ALL}")


def print_error(text: str) -> None:
    """Print an error message."""
    print(f"{Fore.RED}  ✗ {text}{Style.RESET_ALL}")


def print_info(text: str) -> None:
    """Print an info message."""
    print(f"{Fore.WHITE}  ℹ {text}{Style.RESET_ALL}")


def print_item(text: str, indent: int = 4) -> None:
    """Print an indented list item."""
    prefix = " " * indent
    print(f"{prefix}{Fore.WHITE}← {text}{Style.RESET_ALL}")


def print_section(title: str, count: Optional[int] = None, size: Optional[int] = None) -> None:
    """Print a section header with optional count and size."""
    parts = [f"{Fore.CYAN}  📁 {title}/"]
    details = []
    if count is not None:
        details.append(f"{count} files")
    if size is not None:
        details.append(format_size(size))
    if details:
        parts.append(f" ({', '.join(details)})")
    print("".join(parts) + Style.RESET_ALL)


def confirm_action(prompt: str = "Proceed?", default: bool = False) -> bool:
    """Ask user for confirmation.

    Args:
        prompt: The question to ask.
        default: Default answer if user just presses Enter.

    Returns:
        True if user confirmed, False otherwise.
    """
    suffix = " [Y/n] " if default else " [y/N] "
    try:
        response = input(f"{Fore.YELLOW}  {prompt}{suffix}{Style.RESET_ALL}").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print()
        return False

    if not response:
        return default
    return response in ('y', 'yes')
