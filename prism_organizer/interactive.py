"""Interactive prompts for Prism Organizer.

Provides arrow-key navigable menus, checkboxes, and confirmation
dialogs built on the ``questionary`` library.  Falls back to plain
text input when questionary is not installed.
"""

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from prism_organizer.display import (
    get_console, THEME,
    display_header, display_warning,
)


_HAS_QUESTIONARY = False


def _check_questionary() -> bool:
    """Return True if questionary is importable."""
    global _HAS_QUESTIONARY
    if _HAS_QUESTIONARY:
        return True
    try:
        import questionary  # noqa: F401
        _HAS_QUESTIONARY = True
        return True
    except ImportError:
        return False


def _questionary_style():
    """Return a custom questionary style matching the app theme."""
    from questionary import Style
    return Style([
        ("qmark", f"fg:{THEME['primary']} bold"),
        ("question", f"fg:{THEME['info']} bold"),
        ("answer", f"fg:{THEME['accent']} bold"),
        ("pointer", f"fg:{THEME['primary']} bold"),
        ("highlighted", f"fg:{THEME['primary']} bold"),
        ("selected", f"fg:{THEME['success']}"),
        ("separator", f"fg:{THEME['muted']}"),
        ("instruction", f"fg:{THEME['muted']}"),
        ("text", f"fg:{THEME['info']}"),
        ("disabled", f"fg:{THEME['muted']} italic"),
    ])


# ── Interactive confirm ───────────────────────────────────────────────


def interactive_confirm(
    message: str = "Proceed?",
    default: bool = False,
) -> bool:
    """Arrow-key confirm prompt.  Falls back to text input.

    Args:
        message: The yes/no question.
        default: Default answer if user presses Enter.

    Returns:
        True if confirmed.
    """
    if not _check_questionary():
        suffix = " [Y/n] " if default else " [y/N] "
        try:
            resp = input(f"  {message}{suffix}").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print()
            return False
        return resp in ("y", "yes") if resp else default

    import questionary
    return questionary.confirm(
        message,
        default=default,
        style=_questionary_style(),
    ).unsafe_ask() or False


# ── Single select ─────────────────────────────────────────────────────


def interactive_select(
    message: str,
    choices: Sequence[Any],
    default: Optional[str] = None,
    format_fn: Optional[Callable[[Any], str]] = None,
) -> Optional[str]:
    """Arrow-key single-select from a list.

    Args:
        message: Prompt question.
        choices: List of selectable strings or objects.
        default: Default choice label.
        format_fn: Function to format each choice into a string.

    Returns:
        The selected choice label (or None if cancelled).
    """
    if not _check_questionary():
        print(f"\n  {message}")
        for i, c in enumerate(choices, 1):
            label = format_fn(c) if format_fn else str(c)
            print(f"    {i}. {label}")
        try:
            sel = input(f"  Enter number (1-{len(choices)}): ").strip()
        except (KeyboardInterrupt, EOFError):
            return None
        if sel.isdigit():
            idx = int(sel) - 1
            if 0 <= idx < len(choices):
                return choices[idx]
        return None

    import questionary
    styled_choices = []
    for c in choices:
        label = format_fn(c) if format_fn else str(c)
        styled_choices.append(questionary.Choice(title=label, value=c))

    return questionary.select(
        message,
        choices=styled_choices,
        default=default,
        style=_questionary_style(),
        use_indicator=True,
        qmark="\u25b6",
    ).unsafe_ask()


# ── Multi-select / checkbox ───────────────────────────────────────────


def interactive_checkbox(
    message: str,
    choices: Sequence[Any],
    checked: Optional[Sequence[Any]] = None,
    format_fn: Optional[Callable[[Any], str]] = None,
) -> List[Any]:
    """Checkbox multi-select with arrow keys + space to toggle.

    Args:
        message: Prompt question.
        choices: List of selectable items.
        checked: List of pre-selected items.
        format_fn: Function to format each choice into a string.

    Returns:
        List of selected items.
    """
    if not _check_questionary():
        print(f"\n  {message}")
        prechecked = set(checked or [])
        for i, c in enumerate(choices, 1):
            label = format_fn(c) if format_fn else str(c)
            status = "[x]" if c in prechecked else "[ ]"
            print(f"    {i:2}. {status} {label}")
        print(f"  Enter numbers separated by commas (e.g., 1,3,5)")
        try:
            sel = input("  > ").strip()
        except (KeyboardInterrupt, EOFError):
            return list(prechecked)
        if not sel:
            return list(prechecked)
        indices = []
        for part in sel.split(","):
            part = part.strip()
            if part.isdigit():
                idx = int(part) - 1
                if 0 <= idx < len(choices):
                    indices.append(idx)
        return [choices[i] for i in indices] if indices else list(prechecked)

    import questionary
    styled = []
    checked_set = set(checked or [])
    for c in choices:
        label = format_fn(c) if format_fn else str(c)
        styled.append(questionary.Choice(
            title=label,
            value=c,
            checked=c in checked_set,
        ))

    return questionary.checkbox(
        message,
        choices=styled,
        style=_questionary_style(),
        qmark="\u25b6",
        instruction="(space to toggle, enter to confirm)",
    ).unsafe_ask() or []


# ── Text input ────────────────────────────────────────────────────────


def interactive_text(
    message: str,
    default: str = "",
    validate: Optional[Callable[[str], bool]] = None,
) -> Optional[str]:
    """Text input prompt.

    Args:
        message: The question.
        default: Default value shown in placeholder.
        validate: Optional validator returning True if valid.

    Returns:
        User input or None if cancelled.
    """
    if not _check_questionary():
        try:
            val = input(f"  {message} [{default}]: ").strip()
        except (KeyboardInterrupt, EOFError):
            return None
        return val if val else default

    import questionary
    return questionary.text(
        message,
        default=default,
        validate=validate,
        style=_questionary_style(),
        qmark="\u25b6",
    ).unsafe_ask()


# ── Cloud drive selection ─────────────────────────────────────────────


def interactive_cloud_drive_selection(
    drives: List[Any],
) -> Tuple[List[Any], List[Any]]:
    """Let user pick which cloud drives to skip vs include.

    Uses checkbox when questionary is available, falls back to
    the existing text-based prompt otherwise.

    Args:
        drives: List of ``DetectedDrive`` objects with ``name``,
            ``path``, and ``skip`` attributes.

    Returns:
        Tuple of (skip_list, include_list).
    """
    display_header("☁  Cloud Drives Detected")

    if not _check_questionary():
        # Fallback to original manual prompt
        from prism_organizer.cloud_drives import DetectedDrive
        drives_list: List[DetectedDrive] = list(drives)

        import questionary  # noqa — we know it's not available
        print()
        for i, d in enumerate(drives_list, 1):
            status = "[SKIP]" if d.skip else "[INCLUDE]"
            print(f"  {i}. {d.name:<15} {str(d.path):<35} {status}")

        print(f"\n  [S] Skip all  |  [A] Include all  |  [E] Edit")
        try:
            ch = input("  Choose [S/E/A]: ").strip().upper()
        except (KeyboardInterrupt, EOFError):
            ch = "S"

        if ch == "A":
            for d in drives_list:
                d.skip = False
        elif ch == "E":
            for d in drives_list:
                try:
                    sub = input(
                        f"  {d.name:<15} [{'SKIP' if d.skip else 'INCLUDE'}] -> "
                    ).strip().upper()
                except (KeyboardInterrupt, EOFError):
                    break
                if sub == "I":
                    d.skip = False
                elif sub == "S":
                    d.skip = True
        else:
            for d in drives_list:
                d.skip = True

        skip = [d for d in drives_list if d.skip]
        include = [d for d in drives_list if not d.skip]
        return skip, include

    # Rich + questionary path
    import questionary
    console = get_console()

    choices = []
    checked_paths = []
    for d in drives:
        label = f"{d.name:<16} {str(d.path)}"
        choices.append(questionary.Choice(
            title=label,
            value=d,
            checked=d.skip,
        ))
        if d.skip:
            checked_paths.append(d)

    console.print(
        "  These sync folders were detected.  Skip them to avoid\n"
        "  conflicts, or include them to organize their contents.\n",
        style=THEME["muted"],
    )

    selected = questionary.checkbox(
        "Select folders to SKIP (space to toggle, enter to confirm)",
        choices=choices,
        style=_questionary_style(),
        qmark="\u25b6",
        instruction="(space = toggle, enter = confirm)",
    ).unsafe_ask()

    if selected is None:
        # User cancelled — skip all
        for d in drives:
            d.skip = True
        return list(drives), []

    selected_set = set(selected or [])
    for d in drives:
        d.skip = d in selected_set

    skip = [d for d in drives if d.skip]
    include = [d for d in drives if not d.skip]
    return skip, include
