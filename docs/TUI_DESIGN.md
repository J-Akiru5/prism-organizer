# TUI Visual Design

This document records where the interactive TUI's (`prism-organizer tui`) color
palette and status-bar layout come from, how the design tokens map onto
`prism_organizer/display.py`'s `THEME` dict, and what was deliberately left
out of the implementation pass so a future contributor doesn't have to
re-derive any of this from git history.

## Source

The visual design was authored as a set of terminal-chrome mockups
("Prism Organizer TUI Mockups") built against the **Ghost Glow** design
system (Syntaxure Labs), covering two states:

- **Screen 1 — Main dashboard, idle.** The menu, quick stats, activity
  log, and a status-bar footer (`● READY`, current directory, runtime
  versions).
- **Screen 2 — Dry-run preview ("Sort files").** A confirm-before-write
  operation summary and a planned-moves-by-category table, with the
  status bar showing `● AWAITING CONFIRM`.

Only Screen 1's idle status bar is implemented (see [Scope decisions](#scope-decisions-what-this-pass-did-not-do) below).

## Token mapping

`THEME` in [`prism_organizer/display.py`](../prism_organizer/display.py) maps
directly onto the design system's color tokens:

| `THEME` key  | Value      | Ghost Glow token         | Used for                                   |
|--------------|------------|---------------------------|---------------------------------------------|
| `primary`    | `#22d3ee`  | `--color-cyan-bright`     | Headers, active borders, numeric shortcuts, prompts |
| `accent`     | `#a78bfa`  | `--color-purple-bright`   | Menu icon badges, section titles           |
| `accent_ai`  | `#ec4899`  | `--color-pink`            | The AI-classify menu badge specifically    |
| `success`    | `#34d399`  | `--color-emerald-bright`  | `[OK]` log entries, the `● READY` status   |
| `warning`    | `#fbbf24`  | `--color-amber-bright`    | `[WARN]` log entries, confirmations        |
| `error`      | `#f87171`  | `--status-danger`         | `[ERR]` log entries                        |
| `info`       | `#ededed`  | `--color-ink`              | Primary text                               |
| `muted`      | `dim white`| (n/a — see below)          | Secondary/quiet text                       |
| `border`     | `dim cyan` | (n/a — see below)          | Subtle panel borders                       |

`muted` and `border` intentionally do **not** use a fixed hex value from the
design tokens (`--text-tertiary`, `--border-subtle`, etc. are semi-transparent
whites meant for a fixed `#050505` canvas). A terminal isn't a fixed canvas —
users run light-background terminals too — so these two keys keep Rich's
*relative* `dim`/named-grey styling, which adapts to whatever
foreground/background the user's own terminal theme uses. The bright accent
and status colors read fine on both light and dark backgrounds, so those are
safe to hardcode.

Colors are stored as truecolor hex strings; Rich automatically downgrades
them to the nearest 256-color/16-color equivalent on terminals without 24-bit
color support, so this is safe on any Rich-supported terminal without extra
branching.

## What changed in `prism_organizer/tui.py`

- **Banner** (`_make_banner`): now uses the 🔮 mark (matching
  `display.display_splash()`, which already used it) instead of the old
  `[*]` placeholder, and the `scan | sort | ...` subtitle separators are
  colored with `THEME["border"]` to match the design's dim divider treatment.
- **Menu** (`_make_menu`): icon badges are colored `THEME["accent"]`
  (purple), except the AI classify entry, which gets `THEME["accent_ai"]`
  (pink) to call out the one AI-powered action — matching the mockup's
  treatment exactly. Numeric shortcuts stay cyan.
- **Status bar** (`_make_status_bar`, new): a footer panel showing
  `● READY`, the current working directory, and runtime versions
  (`PY_x.x.x · RICH_x.x.x · Vx.x.x`), wired into `_build_layout()` as a new
  `"footer"` row. Only shown on terminals with enough vertical room
  (`>= 26` lines) — same defensive size-based fallback pattern the banner
  and stats panel already use, so it never crowds out the menu on a small
  terminal.

## Windows console encoding safety

Rich's Windows console renderer (`legacy_windows_render`, used automatically
when it detects a Windows console without ANSI/VT support) writes text
through the process's actual `sys.stdout`. If the console's active code page
isn't UTF-8 (the common case is `cp1252` on many locales' default `cmd.exe`/
PowerShell sessions), any character outside that code page raises
`UnicodeEncodeError`. Rich has its own downgrade logic for the box-drawing
characters it uses for **panel borders**, but *not* for arbitrary Unicode a
caller embeds directly in panel **content** — and the TUI's full-screen draw
path (`_tui_print()`) swallows exceptions so the screen keeps redrawing
across terminal resizes, which means an unguarded character wouldn't just
render oddly, it would **silently blank the entire dashboard**.

`prism_organizer/tui.py` guards every such glyph with `_emoji_safe(glyph,
ascii_fallback)`, which checks `sys.stdout.encoding` before deciding whether
to use the glyph or its plain-ASCII fallback:

| Call site                                   | Glyph | ASCII fallback |
|----------------------------------------------|-------|-----------------|
| `_make_banner()`                              | 🔮    | `[*]`           |
| `_make_status_bar()`                          | ●     | `*`             |
| `_make_help_panel()` section dividers         | ━━━   | `===`           |
| `get_user_choice()` input-prompt rule         | ─     | `-`             |
| `run_tui()` cloud-drive-detected log line     | ☁     | `[cloud]`       |

The last two predate this design-import pass — they were already unguarded
bugs, reachable from the every-keystroke input prompt and from a first-run
cloud-drive warning, respectively. They're fixed here because they're the
exact same bug class as what this pass introduced, in the same file, and
"ready for production" isn't true while they're still live.

`tests/test_tui.py` covers `_emoji_safe()` directly (both branches, plus a
missing-encoding edge case) and asserts each guarded builder function
actually emits the ASCII fallback under a mocked `cp1252` stdout and the real
glyph under `utf-8`.

## Scope decisions: what this pass did *not* do

- **Dynamic status states.** The mockup's dry-run preview screen shows the
  status bar as `● AWAITING CONFIRM` (amber) instead of `● READY` (green).
  Driving that from the TUI would mean threading a status callback through
  `prism_organizer/preview.py`'s confirm flow, which is shared with the
  non-interactive CLI path — a larger, separate refactor. The status bar
  implemented here always reflects the idle `● READY` state. A follow-up
  could add a `status: str` parameter to `_make_status_bar()` and pass it
  from the action handlers in `tui.py` around each preview/confirm call.
- **The dry-run preview screen's table layout.** The "Planned Moves by
  Category" table in the mockup already has an equivalent in
  `prism_organizer/preview.py`'s `show_sort_preview()`; this pass didn't
  touch that file. Restyling it to the Ghost Glow palette is a reasonable
  next step but out of scope here.
