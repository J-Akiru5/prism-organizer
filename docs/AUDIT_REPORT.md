# Prism Organizer Open Source Audit Report

Date: 2026-05-23
Repository: prism-organizer (branch: develop)
Scope: Codebase review, packaging, privacy, and open source readiness
Method: Static review of source files and repository artifacts. No runtime execution.

## Summary

- Overall risk: Moderate
- Strengths: Clear safety features, backups for destructive actions, and explicit AI privacy guidance.
- Gaps: Cloud-drive safety not wired, local artifacts in repo, and missing open source governance docs.

## Findings

### Medium Severity

1) Cloud-drive safety is not wired into CLI or TUI
- Impact: Users may organize files inside synced folders, leading to sync conflicts or unintended changes. This contradicts the documented safety promise.
- Evidence: Cloud detection is implemented but not used in command flows. See [prism_organizer/cli.py](prism_organizer/cli.py) and [prism_organizer/cloud_drives.py](prism_organizer/cloud_drives.py).
- Recommendation: Wire detection into CLI and TUI actions, add explicit flags to skip or include, and persist user choice.

2) Repository contains local artifacts with personal paths
- Impact: Leaks local machine paths and file names; looks unprofessional for open source.
- Evidence: [build_log.txt](build_log.txt), [scan_result.txt](scan_result.txt), [stdout_tui.txt](stdout_tui.txt), [stderr_tui.txt](stderr_tui.txt).
- Recommendation: Remove these from source control and add them to ignore rules if they are dev-only artifacts.

3) Developer-only scripts include destructive behavior and hard-coded local paths
- Impact: Accidental misuse and leakage of local environment details.
- Evidence: [run_purge.py](run_purge.py), [scan_targeted.py](scan_targeted.py), [scan_c.py](scan_c.py).
- Recommendation: Move to an internal tools folder excluded from releases, or remove entirely before open sourcing.

4) Binary download allows missing checksum verification
- Impact: Supply-chain risk if a release checksum is missing or not enforced.
- Evidence: [bin/prism-organizer.js](bin/prism-organizer.js).
- Recommendation: Require a checksum match for all releases and fail closed if a checksum is missing.

### Low Severity

1) CLI dry-run flag is unused and default logic is confusing
- Impact: Users may think the flag changes behavior when it does not.
- Evidence: [prism_organizer/cli.py](prism_organizer/cli.py).
- Recommendation: Use a single, consistent preview/confirm flag and make behavior explicit in help.

2) Help output contains a hard-coded version string
- Impact: Help version can drift from actual release.
- Evidence: [prism_organizer/help.py](prism_organizer/help.py), [prism_organizer/__init__.py](prism_organizer/__init__.py).
- Recommendation: Derive help version from package metadata.

3) Exit banner includes marketing content with no opt-out
- Impact: Some open source users consider this intrusive.
- Evidence: [prism_organizer/display.py](prism_organizer/display.py).
- Recommendation: Gate behind a config flag or environment variable, or remove for open source builds.

4) AI preview reads and sends text snippets to providers
- Impact: Potential privacy concerns if users scan sensitive text files.
- Evidence: [prism_organizer/ai.py](prism_organizer/ai.py), [docs/AI_SETUP.md](docs/AI_SETUP.md).
- Recommendation: Add an explicit consent step, redaction, or a config toggle to disable content previews.

5) Operation logs store full file paths
- Impact: Logs can contain sensitive file names and locations.
- Evidence: [prism_organizer/executor.py](prism_organizer/executor.py).
- Recommendation: Document this clearly and consider an option to redact paths in logs.

## Open Source Readiness Gaps

- Missing governance documents (contribution guide, code of conduct, security policy, changelog).
- No visible CI configuration in the repo for tests or packaging.
- No documented release process for the Python package and the npm wrapper.

## Recommendations (Prioritized)

1) Wire cloud-drive detection into all command paths and TUI flows.
2) Remove local artifacts and developer-only scripts from the public repo.
3) Add open source governance docs and a CI pipeline.
4) Fix version consistency and tighten checksum enforcement.
5) Add explicit privacy controls for AI and logs.

## Suggested Next Steps

- Implement the developer guide in docs/DEV_OPEN_SOURCE_GUIDE.md.
- Run a clean-room scan to ensure no local artifacts remain.
- Tag a release candidate and run tests on a fresh Windows VM.
