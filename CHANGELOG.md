# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
