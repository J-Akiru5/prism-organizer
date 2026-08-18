"""Tests for the TUI dashboard: theme tokens, layout, and the Windows
console encoding-safety guards used by the Ghost Glow visual refresh.

See docs/TUI_DESIGN.md for the design source these values come from.
"""

import os
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest
from rich.style import Style

from prism_organizer import tui
from prism_organizer.config import Config, DEFAULT_CONFIG
from prism_organizer.display import THEME


def _make_config():
    config = Config.__new__(Config)
    config._data = dict(DEFAULT_CONFIG)
    config._config_path = Path("/nonexistent")
    return config


def _panel_source_text(panel) -> str:
    """Pull the raw markup/content string(s) a Panel was built from,
    without going through Console rendering.

    Rich's Console has its own (separately-maintained) logic for
    downgrading box-drawing *borders* on legacy Windows consoles, which
    isn't what these tests are about — they're about content *this
    codebase* embeds directly (emoji, dividers, bullets), which has no
    such built-in safety net. Inspecting the Panel's renderable directly
    sidesteps that and tests exactly the code under our control.
    """
    return _extract_text(panel.renderable)


def _extract_text(node) -> str:
    if isinstance(node, str):
        return node
    if hasattr(node, "plain"):  # rich.text.Text
        return node.plain
    if hasattr(node, "renderables"):  # rich.console.Group
        return " ".join(_extract_text(r) for r in node.renderables)
    if hasattr(node, "renderable"):  # rich.align.Align and similar wrappers
        return _extract_text(node.renderable)
    if hasattr(node, "columns"):  # rich.table.Table / Table.grid
        parts = []
        for column in node.columns:
            parts.extend(str(cell) for cell in getattr(column, "_cells", []))
        return " ".join(parts)
    return ""


# ── Theme ────────────────────────────────────────────────────────────


def test_theme_values_are_valid_rich_styles():
    """Every THEME entry must be a style string Rich can actually parse
    (catches typos in hex codes / style keywords before they hit a
    terminal)."""
    for value in THEME.values():
        Style.parse(value)


def test_theme_has_expected_ghost_glow_tokens():
    """The design-import token set must stay present — menu badges and
    the status bar depend on these specific keys."""
    for key in ("primary", "accent", "accent_ai", "success", "warning",
                "error", "muted", "info", "border", "row_alt"):
        assert key in THEME


# ── _emoji_safe() ────────────────────────────────────────────────────


def test_emoji_safe_falls_back_when_stdout_cannot_encode_it():
    with mock.patch("sys.stdout", SimpleNamespace(encoding="cp1252")):
        assert tui._emoji_safe("\U0001f52e", "[*]") == "[*]"
        assert tui._emoji_safe("●", "*") == "*"
        assert tui._emoji_safe("━━━", "===") == "==="
        assert tui._emoji_safe("─", "-") == "-"


def test_emoji_safe_keeps_the_glyph_when_stdout_supports_it():
    with mock.patch("sys.stdout", SimpleNamespace(encoding="utf-8")):
        assert tui._emoji_safe("\U0001f52e", "[*]") == "\U0001f52e"
        assert tui._emoji_safe("●", "*") == "●"


def test_emoji_safe_treats_missing_encoding_as_ascii():
    with mock.patch("sys.stdout", SimpleNamespace(encoding=None)):
        assert tui._emoji_safe("\U0001f52e", "[*]") == "[*]"


# ── Panel builders: must degrade to ASCII, never crash, on cp1252 ──────
#
# These panels are drawn through the TUI's raw _tui_print() path, which
# (unlike display.py's _safe_print()) has no ASCII-fallback safety net —
# on a Windows console using a non-UTF-8 active code page (e.g. the
# default cp1252 on many locales), sys.stdout.write() raises
# UnicodeEncodeError for a character outside that code page, and
# draw_full_screen() swallows the exception to stay resize-safe. That
# means an un-guarded glyph wouldn't just look wrong — it would silently
# blank the entire dashboard. Each (builder, glyph, ascii_fallback)
# below is a spot this codebase deliberately guards with _emoji_safe().

_GUARDED_GLYPHS = [
    (tui._make_banner, "\U0001f52e", "[*]"),
    (tui._make_status_bar, "●", "*"),
    (tui._make_help_panel, "━━━", "==="),
]


@pytest.mark.parametrize(
    "builder,glyph,fallback", _GUARDED_GLYPHS,
    ids=[b.__name__ for b, _, _ in _GUARDED_GLYPHS],
)
def test_builder_uses_ascii_fallback_under_cp1252(builder, glyph, fallback):
    with mock.patch("sys.stdout", SimpleNamespace(encoding="cp1252")):
        panel = builder()
    text = _panel_source_text(panel)
    assert glyph not in text
    assert fallback in text


@pytest.mark.parametrize(
    "builder,glyph,fallback", _GUARDED_GLYPHS,
    ids=[b.__name__ for b, _, _ in _GUARDED_GLYPHS],
)
def test_builder_keeps_glyph_under_utf8(builder, glyph, fallback):
    with mock.patch("sys.stdout", SimpleNamespace(encoding="utf-8")):
        panel = builder()
    text = _panel_source_text(panel)
    assert glyph in text


@pytest.mark.parametrize("builder", [
    tui._make_banner, tui._make_menu, tui._make_status_bar, tui._make_help_panel,
])
def test_panel_builders_do_not_raise(builder):
    """Baseline smoke test, independent of console encoding."""
    assert builder() is not None


def test_menu_colors_ai_badge_distinctly_from_other_badges():
    """The AI classify entry should get the design's pink accent, not
    the purple used for every other menu icon badge."""
    text = _panel_source_text(tui._make_menu())
    assert THEME["accent_ai"] in text
    assert THEME["accent"] in text


def test_stats_panel_renders(tmp_path):
    config = _make_config()
    config._data["default_paths"] = [str(tmp_path)]
    (tmp_path / "a.txt").write_text("x")
    assert tui._make_stats_panel(config) is not None


# ── Layout ───────────────────────────────────────────────────────────


@pytest.mark.parametrize("lines", [10, 18, 24, 30])
def test_build_layout_handles_every_terminal_size_branch(lines):
    """Small terminals drop the banner/footer; only large ones get the
    new status-bar footer row — verify every branch still builds."""
    config = _make_config()
    fake_size = os.terminal_size((120, lines))
    with mock.patch("os.get_terminal_size", return_value=fake_size):
        layout = tui._build_layout(config)
    names = {child.name for child in layout.children}
    assert "main" in names
    if lines >= 26:
        assert "footer" in names
    else:
        assert "footer" not in names
