"""Display abstraction layer for Prism Organizer.

Uses the ``rich`` library when available, falling back to the existing
colorama-based helpers in :mod:`prism_organizer.utils`.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

from prism_organizer.utils import (
    format_size,
    print_header,
    print_success,
    print_warning,
    print_error,
    print_info,
    confirm_action,
)

_RICH_AVAILABLE = False
_console = None


def _init_rich() -> bool:
    """Try to import rich and return True if available."""
    global _RICH_AVAILABLE, _console
    if _RICH_AVAILABLE:
        return True
    try:
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        from rich.progress import (
            Progress, SpinnerColumn, BarColumn, TextColumn,
            TimeElapsedColumn, TimeRemainingColumn,
        )
        from rich.text import Text
        from rich import box
        _console = Console()
        _RICH_AVAILABLE = True
        return True
    except ImportError:
        return False


def rich_available() -> bool:
    """Check whether the ``rich`` library can be imported."""
    return _init_rich()


def get_console():
    """Get the Rich console (initialises on first call)."""
    _init_rich()
    return _console


# ── Table helpers ────────────────────────────────────────────────────


def display_table(
    title: str,
    columns: Sequence[Dict[str, Any]],
    rows: Sequence[Sequence[Any]],
    caption: Optional[str] = None,
) -> None:
    """Display tabular data using Rich (if available) or plain text.

    Args:
        title: Table title.
        columns: List of dicts with ``header`` and optionally ``style``,
            ``justify``, ``width``.
        rows: Row data matching the column order.
        caption: Optional footer text.
    """
    if not _init_rich():
        # Fallback: plain ASCII table
        print(f"\n  ── {title} ──")
        header = "  " + "  ".join(
            f"{c['header']:>{c.get('width', 12)}}" for c in columns
        )
        print(header)
        print("  " + "─" * (len(header) - 2))
        for row in rows[:50]:
            formatted = []
            for i, val in enumerate(row):
                width = columns[i].get("width", 12)
                formatted.append(f"{str(val):>{width}}")
            print("  " + "  ".join(formatted))
        if caption:
            print(f"  {caption}")
        return

    from rich.table import Table
    from rich import box

    table = Table(
        title=title,
        box=box.ROUNDED,
        title_style="bold cyan",
        border_style="dim blue",
        caption=caption,
        caption_style="dim",
    )
    for col in columns:
        table.add_column(
            col["header"],
            style=col.get("style", ""),
            justify=col.get("justify", "left"),
            width=col.get("width"),
        )
    for row in rows:
        table.add_row(*[str(v) for v in row])
    _console.print(table)


# ── Rich replacements for core display functions ─────────────────────


def display_header(text: str) -> None:
    """Print a styled header (Rich panel or colorama fallback)."""
    if _init_rich():
        from rich.panel import Panel
        from rich.text import Text
        _console.print(Panel(
            Text(text, style="bold cyan"),
            border_style="cyan",
            expand=False,
        ))
    else:
        print_header(text)


def display_success(text: str) -> None:
    """Print a success message with a check mark."""
    if _init_rich():
        _console.print(f"  [green]✓[/green] {text}")
    else:
        print_success(text)


def display_warning(text: str) -> None:
    """Print a warning message."""
    if _init_rich():
        _console.print(f"  [yellow]⚠[/yellow] {text}")
    else:
        print_warning(text)


def display_error(text: str) -> None:
    """Print an error message."""
    if _init_rich():
        _console.print(f"  [red]✗[/red] {text}")
    else:
        print_error(text)


def display_info(text: str) -> None:
    """Print an informational message."""
    if _init_rich():
        _console.print(f"  [dim]ℹ[/dim] {text}")
    else:
        print_info(text)


def display_confirm(prompt: str = "Proceed?", default: bool = False) -> bool:
    """Ask user for confirmation (Rich prompt or colorama fallback)."""
    if _init_rich():
        suffix = " [Y/n]" if default else " [y/N]"
        try:
            response = input(f"  {prompt}{suffix} ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print()
            return False
        if not response:
            return default
        return response in ("y", "yes")
    return confirm_action(prompt, default)


def display_progress_bar(
    iterable: Sequence[Any],
    desc: str = "Working",
    unit: str = "item",
    **kwargs,
):
    """Return an iterable with a progress bar (Rich or tqdm fallback).

    When Rich is available the bar includes elapsed / remaining time.
    When not, the existing tqdm-based bars are used unchanged
    (callers should use tqdm directly in that case).

    Yields:
        Items from *iterable* with wrapping progress.
    """
    if not _init_rich():
        # Fall back to tqdm — caller handles this
        from tqdm import tqdm
        yield from tqdm(iterable, desc=desc, unit=unit, **kwargs)
        return

    from rich.progress import (
        Progress, BarColumn, TextColumn,
        TimeElapsedColumn, TimeRemainingColumn,
    )

    with Progress(
        TextColumn(f"  {desc}"),
        BarColumn(bar_width=30),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        transient=False,
    ) as progress:
        task = progress.add_task(desc, total=len(iterable))
        for item in iterable:
            yield item
            progress.advance(task)


# ── Specific report displays ─────────────────────────────────────────


def display_scan_summary(
    target_dir: Path,
    total_files: int,
    total_size: int,
    total_dirs: int,
) -> None:
    """Display scan summary as a Rich panel or plain text."""
    if _init_rich():
        from rich.panel import Panel
        content = (
            f"[bold]Target:[/bold]      {target_dir}\n"
            f"[bold]Total files:[/bold]  [cyan]{total_files:,}[/cyan]\n"
            f"[bold]Total size:[/bold]   [cyan]{format_size(total_size)}[/cyan]\n"
            f"[bold]Directories:[/bold]  [cyan]{total_dirs:,}[/cyan]"
        )
        _console.print(Panel(content, title="Scan Summary", border_style="cyan"))
    else:
        print(f"\n  Target:      {target_dir}")
        print(f"  Total files:  {total_files:,}")
        print(f"  Total size:   {format_size(total_size)}")
        print(f"  Directories:  {total_dirs:,}")


def display_category_table(
    categories: Dict[str, Dict[str, int]],
    max_rows: int = 0,
) -> None:
    """Display category breakdown in a table."""
    sorted_cats = sorted(
        categories.items(),
        key=lambda x: x[1].get("size", 0),
        reverse=True,
    )[:max_rows] if max_rows else sorted(
        categories.items(),
        key=lambda x: x[1].get("size", 0),
        reverse=True,
    )

    display_table(
        title="Category Breakdown",
        columns=[
            {"header": "Category", "width": 20},
            {"header": "Count", "justify": "right", "width": 10},
            {"header": "Size", "justify": "right", "width": 14},
        ],
        rows=[
            (cat, f"{info.get('count', 0):,}", format_size(info.get("size", 0)))
            for cat, info in sorted_cats
        ],
    )


def display_top_files(files: List[Any], limit: int = 10) -> None:
    """Display the largest files in a table."""
    display_table(
        title=f"Top {limit} Largest Files",
        columns=[
            {"header": "Size", "justify": "right", "width": 14},
            {"header": "Name", "width": 50},
        ],
        rows=[
            (format_size(fi.size), fi.name[:47] + "..." if len(fi.name) > 47 else fi.name)
            for fi in files[:limit]
        ],
    )


def display_findings(warnings: List[str]) -> None:
    """Display scan findings / warnings."""
    if not warnings:
        return
    if _init_rich():
        from rich.panel import Panel
        lines = "\n".join(f"  • {w}" for w in warnings)
        _console.print(Panel(
            lines,
            title="[yellow]⚠ Findings[/yellow]",
            border_style="yellow",
        ))
    else:
        for w in warnings:
            print_warning(w)


def display_operation_summary(
    command: str,
    target_dir: str,
    count: int,
    size: int,
    extra: Optional[List[tuple]] = None,
) -> None:
    """Display an operation summary panel."""
    if _init_rich():
        from rich.panel import Panel
        lines = [
            f"[bold]Command:[/bold]  {command}",
            f"[bold]Target:[/bold]   {Path(target_dir)}",
            f"[bold]Items:[/bold]    [cyan]{count:,}[/cyan]",
            f"[bold]Size:[/bold]     [cyan]{format_size(size)}[/cyan]",
        ]
        if extra:
            for label, value in extra:
                lines.append(f"[bold]{label}:[/bold] {value}")
        _console.print(Panel(
            "\n".join(lines),
            title="Operation Preview",
            border_style="cyan",
        ))
    else:
        print(f"\n  Command:  {command}")
        print(f"  Target:   {target_dir}")
        print(f"  Items:    {count:,}")
        print(f"  Size:     {format_size(size)}")
        if extra:
            for label, value in extra:
                print(f"  {label}: {value}")
