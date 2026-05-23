# Developer Guide: Open Source Readiness

Target deadline: 2026-05-28 (5 working days)
Goal: Make the repository safe, professional, and ready for public contribution.

## Phase 1: Remove Local Artifacts (Day 1)

Tasks:
- Remove local build and scan outputs from the repo.
- Remove or relocate developer-only scripts that contain hard-coded paths.

Files to review:
- build_log.txt, scan_result.txt, stdout_tui.txt, stderr_tui.txt
- run_purge.py, scan_targeted.py, scan_c.py

Acceptance criteria:
- Repo has no local machine paths or user-specific data.
- Developer-only scripts are not shipped in releases.

## Phase 2: Cloud-Drive Safety Wiring (Day 1-2)

Goal: Ensure cloud-drive detection actually runs for CLI and TUI workflows.

Implementation plan:
1) CLI
- Replace the stub in _detect_cloud_drives with real detection.
- Use CloudDriveDetector.detect and then prompt with interactive selection.
- Add flags to control behavior:
  - --skip-cloud-drives (default)
  - --include-cloud-drives
  - --no-cloud-detect

2) TUI
- On startup, detect cloud drives once.
- Allow the user to skip or include via the existing interactive selection.
- Cache the decision in memory for the session.

Acceptance criteria:
- CLI and TUI both honor cloud-drive skip lists.
- Behavior matches the README safety promises.

## Phase 3: Version and Packaging Consistency (Day 2-3)

Tasks:
- Centralize version strings (Python __init__, setup.py, package.json, npm wrapper, help text).
- Update help output to use runtime version instead of a hard-coded string.
- For the npm wrapper, fail closed if a checksum is missing.

Acceptance criteria:
- One source of truth for version.
- Help shows the correct version.
- Binary download always verifies checksum.

## Phase 4: Open Source Governance Docs (Day 3)

Add the following documents:
- Contribution guide
- Code of conduct
- Security policy
- Changelog or release notes

Acceptance criteria:
- New contributors know how to report issues, submit PRs, and report security problems.

## Phase 5: CI and QA (Day 4)

Tasks:
- Add a CI workflow to run tests and basic linting on Windows.
- Add a smoke test for CLI startup and help output.

Acceptance criteria:
- CI runs on every PR.
- Tests pass on Windows.

## Phase 6: Privacy and UX Polish (Day 5)

Tasks:
- Add a config flag or environment variable to disable the exit banner.
- Add a config toggle to disable AI content previews or require explicit consent.
- Document that logs contain full file paths.

Acceptance criteria:
- Users can opt out of marketing and AI content previews.
- Privacy disclosures are clear in the docs.

## Optional Enhancements

- Add a minimal threat model section to the README.
- Add a release checklist (bump version, update checksums, build binary, publish).
- Add issue templates for bug reports and feature requests.

## Verification Checklist

- No local artifacts or user paths in repo.
- Cloud-drive detection works for CLI and TUI.
- Help version matches package version.
- CI passes on a clean Windows VM.
- Open source docs are present and readable.
