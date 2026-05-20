"""Display abstraction layer for Prism Organizer.

Uses the ``rich`` library for all terminal output.  Provides
beautiful, consistent styling matching the application theme:
cyan primary, purple accent, green/yellow/red status.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from rich.console import Console, Group
from rich.table import Table
from rich.panel import Panel
from rich.progress import (
    Progress, SpinnerColumn, BarColumn, TextColumn,
    TimeElapsedColumn, TimeRemainingColumn, MofNCompleteColumn,
    TaskProgressColumn,
)
from rich.text import Text
from rich.layout import Layout
from rich.align import Align
from rich.columns import Columns
from rich.live import Live
from rich import box
from rich.style import Style
from rich.tree import Tree

from prism_organizer.utils import format_size

# ── Theme ─────────────────────────────────────────────────────────────

THEME = {
    "primary": "cyan",
    "accent": "magenta",
    "success": "green",
    "warning": "yellow",
    "error": "red",
    "muted": "dim white",
    "info": "white",
    "border": "dim cyan",
}

CATEGORY_EMOJI = {
    "Images": "\U0001f5bc",          # 🖼
    "Documents": "\U0001f4c4",        # 📄
    "Spreadsheets": "\U0001f4ca",     # 📊
    "Presentations": "\U0001f4bd",    # 💽
    "Videos": "\U0001f3ac",           # 🎬
    "Audio": "\U0001f3b5",             # 🎵
    "Archives": "\U0001f4e6",          # 📦
    "Code": "\U0001f4bb",              # 💻
    "Installers": "\U0001f4be",        # 💾
    "Databases": "\U0001f6e1",          # 🛡
    "Design": "\U0001f3a8",             # 🎨
    "Fonts": "\U0001f524",              # 🔤
    "Misc": "\U0001f4c1",               # 📁
}

_console: Optional[Console] = None


def get_console() -> Console:
    """Get (or create) the Rich console instance."""
    global _console
    if _console is None:
        _console = Console()
    return _console


def rich_available() -> bool:
    """Always True — rich is now a required dependency."""
    return True


# ── Splash / Header ───────────────────────────────────────────────────


def display_splash() -> None:
    """Print the application splash banner."""
    console = get_console()
    banner = Panel(
        Align.center(
            Group(
                Text("", style=""),
                Text(
                    " \U0001f52e  Prism Organizer",
                    style=f"bold {THEME['accent']}",
                ),
                Text(
                    f"v1.1.0 — scan, sort, clean, organize",
                    style=THEME["muted"],
                ),
                Text("", style=""),
            ),
            vertical="middle",
        ),
        box=box.DOUBLE,
        border_style=THEME["border"],
        width=62,
    )
    console.print(banner)


def display_header(text: str, style: Optional[str] = None) -> None:
    """Print a styled section header.

    Args:
        text: Header text.
        style: Override style (default: bold cyan).
    """
    console = get_console()
    st = style or f"bold {THEME['primary']}"
    panel = Panel(
        Text(text, style=st),
        box=box.HEAVY,
        border_style=THEME["primary"],
        padding=(0, 2),
    )
    console.print(panel)


def display_subheader(text: str) -> None:
    """Print a smaller sub-section header."""
    console = get_console()
    console.print()
    console.rule(
        f"[bold {THEME['primary']}]{text}[/]",
        style=THEME["border"],
    )


# ── Status Messages ───────────────────────────────────────────────────


def display_success(text: str) -> None:
    """Print a green success message."""
    get_console().print(
        f"  [{THEME['success']}]✓[/{THEME['success']}] {text}"
    )


def display_warning(text: str) -> None:
    """Print a yellow warning message."""
    get_console().print(
        f"  [{THEME['warning']}]⚠[/{THEME['warning']}] {text}"
    )


def display_error(text: str) -> None:
    """Print a red error message."""
    get_console().print(
        f"  [{THEME['error']}]✗[/{THEME['error']}] {text}"
    )


def display_info(text: str) -> None:
    """Print a muted info message."""
    get_console().print(
        f"  [{THEME['muted']}]ℹ[/{THEME['muted']}] {text}"
    )


# ── Confirmation ──────────────────────────────────────────────────────


def display_confirm(prompt: str = "Proceed?", default: bool = False) -> bool:
    """Simple text-based confirmation (for non-interactive mode).

    For arrow-key selection, use :func:`interactive_confirm` from
    the :mod:`prism_organizer.interactive` module.
    """
    suffix = " [Y/n] " if default else " [y/N] "
    try:
        response = input(f"  {prompt}{suffix}").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print()
        return False
    if not response:
        return default
    return response in ("y", "yes")


# ── Tables ────────────────────────────────────────────────────────────


def display_table(
    title: str,
    columns: Sequence[Dict[str, Any]],
    rows: Sequence[Sequence[Any]],
    caption: Optional[str] = None,
) -> None:
    """Display a styled table.

    Args:
        title: Table title.
        columns: List of column dicts with ``header``, optional
            ``style``, ``justify``, ``width``.
        rows: Row data.
        caption: Optional footer text.
    """
    console = get_console()
    table = Table(
        title=f"[bold {THEME['primary']}]{title}",
        box=box.ROUNDED,
        title_style=f"bold {THEME['primary']}",
        border_style=THEME["border"],
        caption=caption,
        caption_style=THEME["muted"],
        padding=(0, 1),
        expand=False,
    )
    for col in columns:
        table.add_column(
            col["header"],
            style=col.get("style", ""),
            justify=col.get("justify", "left"),
            width=col.get("width"),
            no_wrap=col.get("no_wrap", False),
        )
    for i, row in enumerate(rows):
        row_style = "" if i % 2 == 0 else f"on {THEME['muted']}"
        table.add_row(*[str(v) for v in row], style=row_style)
    console.print(table)


def display_key_value(
    pairs: List[Tuple[str, str]],
    title: Optional[str] = None,
) -> None:
    """Display a set of key-value pairs in a simple panel.

    Args:
        pairs: List of (label, value) tuples.
        title: Optional panel title.
    """
    console = get_console()
    lines = []
    max_label = max(len(p[0]) for p in pairs) if pairs else 0
    for label, value in pairs:
        lines.append(
            f"[bold]{label + ':':<{max_label + 1}}[/bold] "
            f"[{THEME['primary']}]{value}"
        )
    panel = Panel(
        "\n".join(lines),
        title=f"[bold {THEME['primary']}]{title}" if title else None,
        border_style=THEME["border"],
        padding=(0, 2),
    )
    console.print(panel)


# ── Progress Bars ─────────────────────────────────────────────────────


def create_progress(transient: bool = False) -> Progress:
    """Create a themed progress bar.

    Args:
        transient: If True, the bar disappears when done.

    Returns:
        A Rich ``Progress`` instance ready for use as a context manager.
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(
            bar_width=30,
            style=THEME["muted"],
            complete_style=THEME["primary"],
            finished_style=THEME["success"],
        ),
        TaskProgressColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        transient=transient,
        expand=False,
    )


def display_progress(
    iterable: Sequence[Any],
    desc: str = "Working",
    unit: str = "item",
    total: Optional[int] = None,
) -> Any:
    """Iterate with a themed progress bar.

    Yields items from *iterable* with progress tracking.

    Args:
        iterable: Items to iterate over.
        desc: Description label.
        unit: Unit name.
        total: Total count (auto-detected if None).

    Yields:
        Each item from the iterable.
    """
    total = total or len(iterable)
    with create_progress() as progress:
        task = progress.add_task(
            f"  {desc}",
            total=total,
            completed=0,
        )
        for item in iterable:
            yield item
            progress.advance(task)


# ── Category & File Display ───────────────────────────────────────────


def display_category_icon(category: str) -> str:
    """Get the emoji icon for a file category."""
    return CATEGORY_EMOJI.get(category, CATEGORY_EMOJI["Misc"])


def display_category_tree(
    categories: Dict[str, Dict[str, int]],
    max_files_per: int = 5,
    sample_files: Optional[Dict[str, List[str]]] = None,
) -> None:
    """Display categories as a Rich tree with emoji icons.

    Args:
        categories: Category → {count, size} mapping.
        max_files_per: Max sample filenames per category.
        sample_files: Optional category → [filenames] for samples.
    """
    console = get_console()
    tree = Tree(
        f"[bold {THEME['primary']}]Directory Contents",
        guide_style=THEME["muted"],
    )

    sorted_cats = sorted(
        categories.items(),
        key=lambda x: x[1].get("size", 0),
        reverse=True,
    )

    for cat, info in sorted_cats:
        icon = display_category_icon(cat)
        count = info.get("count", 0)
        size = info.get("size", 0)
        label = (
            f"{icon}  [bold]{cat}[/bold]  "
            f"[{THEME['muted']}]{count:,} files  •  "
            f"{format_size(size)}[/{THEME['muted']}]"
        )
        branch = tree.add(label)
        if sample_files and cat in sample_files:
            for fname in sample_files[cat][:max_files_per]:
                branch.add(f"[{THEME['muted']}]{fname}")

    console.print()
    console.print(tree)
    console.print()


def display_top_files_list(
    files: List[Any],
    limit: int = 10,
    unit: str = "largest",
) -> None:
    """Display top files as a compact list with size bars.

    Args:
        files: List of FileInfo objects.
        limit: Max files to show.
        unit: Description ("largest", "oldest", etc.).
    """
    console = get_console()

    if not files:
        return

    max_size = files[0].size if files else 1
    max_name_len = max(
        (len(fi.name[:45]) for fi in files[:limit]), default=20
    )

    lines = [
        f"[bold {THEME['primary']}]Top {limit} {unit.title()} Files"
        f"[/bold {THEME['primary']}]",
    ]
    for i, fi in enumerate(files[:limit], 1):
        name = fi.name[:45] + "..." if len(fi.name) > 45 else fi.name
        size_str = format_size(fi.size)
        bar_width = max(1, int((fi.size / max_size) * 15))
        bar = "\u2588" * bar_width
        lines.append(
            f"  {i:2}. [{THEME['info']}]{name:<{max_name_len + 3}}"
            f"[/{THEME['info']}] "
            f"[{THEME['primary']}]{size_str:>12}[/{THEME['primary']}]  "
            f"[{THEME['muted']}]{bar}"
        )

    console.print(f"\n  {'─' * 50}")
    console.print("\n".join(lines))
    console.print(f"  {'─' * 50}")


# ── Scan Report Components ────────────────────────────────────────────


def display_scan_summary(
    target_dir: Path,
    total_files: int,
    total_size: int,
    total_dirs: int,
) -> None:
    """Display scan summary in a panel."""
    display_key_value(
        pairs=[
            ("Target", str(target_dir)),
            ("Files", f"{total_files:,}"),
            ("Size", format_size(total_size)),
            ("Dirs", f"{total_dirs:,}"),
        ],
        title="Scan Summary",
    )


def display_category_table(
    categories: Dict[str, Dict[str, int]],
    max_rows: int = 0,
) -> None:
    """Display category breakdown as a table."""
    sorted_cats = sorted(
        categories.items(),
        key=lambda x: x[1].get("size", 0),
        reverse=True,
    )
    if max_rows:
        sorted_cats = sorted_cats[:max_rows]

    rows = [
        (
            f"{display_category_icon(cat)} {cat}",
            f"{info.get('count', 0):,}",
            format_size(info.get("size", 0)),
        )
        for cat, info in sorted_cats
    ]
    display_table(
        title="Category Breakdown",
        columns=[
            {"header": "Category", "width": 24},
            {"header": "Count", "justify": "right", "width": 10},
            {"header": "Size", "justify": "right", "width": 14},
        ],
        rows=rows,
    )


def display_top_files(files: List[Any], limit: int = 10) -> None:
    """Display largest files table."""
    rows = [
        (
            format_size(fi.size),
            fi.name[:50] + "..." if len(fi.name) > 50 else fi.name,
        )
        for fi in files[:limit]
    ]
    display_table(
        title=f"Top {limit} Largest Files",
        columns=[
            {"header": "Size", "justify": "right", "width": 14},
            {"header": "Name", "width": 55},
        ],
        rows=rows,
    )


def display_findings(warnings: List[str]) -> None:
    """Display scan findings / warnings."""
    if not warnings:
        return
    console = get_console()
    items = "\n".join(f"  [yellow]•[/yellow] {w}" for w in warnings)
    panel = Panel(
        items,
        title=f"[bold {THEME['warning']}]⚠  Findings",
        border_style=THEME["warning"],
        padding=(0, 2),
    )
    console.print(panel)


# ── Operation Preview ─────────────────────────────────────────────────


def display_operation_summary(
    command: str,
    target_dir: str,
    count: int,
    size: int,
    extra: Optional[List[Tuple[str, str]]] = None,
) -> None:
    """Display an operation summary panel."""
    pairs = [
        ("Command", command),
        ("Target", str(Path(target_dir))),
        ("Items", f"{count:,}"),
        ("Size", format_size(size)),
    ]
    if extra:
        pairs.extend(extra)
    display_key_value(pairs, title="Operation Preview")
