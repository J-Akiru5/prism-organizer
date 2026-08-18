# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.0] - 2026-08-18

### Added
- **TUI Visual Refresh**: The interactive TUI (`prism-organizer tui`) now uses the project's "Ghost Glow" design-system color tokens (see [`docs/TUI_DESIGN.md`](docs/TUI_DESIGN.md) for the full token table and design source) — cyan primary, purple menu badges, and a dedicated pink accent for the AI classify action.
- **TUI Status Bar**: A new footer panel shows a `● READY` indicator, the current working directory, and runtime versions (Python / Rich / Prism Organizer), on terminals with enough vertical room.

### Fixed
- **TUI Windows Console Encoding Crashes**: Several TUI screens embedded Unicode characters (an emoji banner mark, section-divider glyphs, a status bullet, the main input prompt's rule line, and a cloud-drive-detection log line) with no fallback for non-UTF-8 Windows console code pages (e.g. the common default `cp1252`). On such a console, `UnicodeEncodeError` inside the TUI's full-screen redraw path was silently swallowed, blanking the entire dashboard instead of just rendering incorrectly. All of these are now guarded with a `sys.stdout`-encoding check that falls back to a plain-ASCII equivalent. Two of the fixed spots (the main input prompt's divider and the cloud-drive log line) predate this release.
- **TUI Help Screen Markup**: Several color spans in the `[H]` help overlay were missing their Rich markup brackets, so the literal color name/hex code printed as garbage text instead of being applied as styling.

## [1.3.3] - 2026-08-18

### Security
- **AI Classification Path Traversal**: `_build_classification_plan()` (`ai-classify` command) built the destination directory as `target_dir / c.suggested_category` directly from unsanitized AI output — a suggested category like `"../../../evil"` would escape `target_dir` entirely (unlike `_build_rename_plan()`, which already ran AI-suggested filenames through `sanitize_suggested_stem()`). AI-suggested categories are now validated against the configured category allow-list (`config.categories.keys()`); any suggestion outside that list falls back to the file's own already-trusted category instead of being trusted as a path segment.

## [1.3.2] - 2026-08-18

### Fixed
- **Monthly Schedule `/D` Value**: `schtasks.exe` rejects a comma-separated day list for `/SC MONTHLY /D` (e.g. `/D 1,15` fails with "Invalid value for /D option") — only a single day is accepted. `TaskScheduler.add_task()` now registers one `schtasks` entry per requested day, named `"<base name> (day N)"`, so `schedule add --interval monthly --days 1,15` actually creates two working tasks instead of one that schtasks silently rejects. Each day is created independently — one failing day no longer blocks the rest, and a summary reports which days succeeded/failed.
- **Monthly Group Removal**: `TaskScheduler.remove_task()` and the `schedule remove` CLI flow now recognize the day-suffixed task group a monthly schedule produces. Removing the shared base name deletes every day-task together; `schedule list` and `schedule remove` now flag which entries belong to the same monthly group so a user isn't left thinking a single removal cleared the whole schedule.

## [1.3.1] - 2026-08-18

### Fixed
- **`schedule add --command` Attribute Collision**: The nested `schedule add --command` argument shared the same `dest` (`args.command`) as the top-level subparser used for command dispatch, so passing `--command` silently overwrote the top-level command and routed execution to the wrong handler (e.g. `cmd_sort` instead of `cmd_schedule`), crashing with `AttributeError`. The nested flag now maps to `args.run_command`, leaving top-level dispatch untouched.

## [1.3.0] - 2026-08-18

### Added
- **Monthly Scheduled Tasks**: `schedule add` now supports `--interval monthly` with a `--days` option (comma-separated days-of-month, e.g. `--days 1,15`) for tasks like twice-a-month cleanups, backed by `schtasks.exe`'s `/SC MONTHLY /D` flags.

## [1.0.0-rc1] - 2026-05-23

### Added
- **Cloud-Drive Safety**: Integrated `CloudDriveDetector` into CLI and TUI pipelines to prevent unintended scanning/modification of cloud-synced folders.
- **CLI Control Flags**: Added `--skip-cloud-drives`, `--include-cloud-drives`, and `--no-cloud-detect` flags for precise cloud scan behaviors.
- **TUI Cloud Detection**: Added cloud-drive detection on startup with session caching and warning confirmations when working inside cloud directories.
- **Open-Source Governance**: Created `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, and `SECURITY.md` guidelines.
- **Exit Banner Suppression**: Added config option `show_exit_banner` and env var `PRISM_NO_BANNER` to disable exit promotional messages.
- **AI Privacy Guardrails**: Added `disable_previews` config toggle to prevent reading file content during classification, and a global `--no-ai` flag to disable AI entirely.

### Changed
- **Dynamic Help Versioning**: The CLI help command now dynamically imports the current version from package metadata or fallback module version instead of displaying a hardcoded string.

### Fixed
- **Repository Sanitation**: Purged local machine artifacts, log files (`build_log.txt`, `scan_result.txt`, `stdout_tui.txt`, `stderr_tui.txt`), and hardened `.gitignore` rules.
- **Dev Tools Quarantine**: Quarantined three developer-only scripts (`run_purge.py`, `scan_targeted.py`, `scan_c.py`) into `.dev-tools/` to avoid publishing developer system specifics.

### Security
- **Fail-Closed npm Checksum**: Hardened npm binary wrapper (`bin/prism-organizer.js`) to fail-closed if download checksum is missing or incorrect, aborting execution and falling back to Python instead of warning and running insecure binaries.
