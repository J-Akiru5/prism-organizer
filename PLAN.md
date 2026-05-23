# Release Plan: Publish Prism Organizer v1.2.16

## Goal
Safely publish the next version of Prism Organizer (`1.2.16`) with all open-source readiness, safety, and security fixes from the `develop` branch merged into `main`.

## Key Action Items
1. **Prepare Version Bump**:
   - Bump version to `1.2.16` in `package.json`.
   - Run `node scripts/sync-version.js` to update version references in Python files, setup configs, and npm wrapper.
2. **Harden GitHub Actions Release Workflow**:
   - Restructure `.github/workflows/publish.yml` to compile the Windows `.exe` on a `windows-latest` runner first.
   - Dynamically compute the SHA-256 hash of the built `.exe`.
   - Inject the computed hash into the NPM wrapper's `CHECKSUM_REGISTRY` before publishing to NPM. This ensures the npm wrapper will successfully match the executable download checksum.
3. **Merge and Push**:
   - Checkout `main`, merge `develop` into `main`, and push to remote.
   - Tag the release as `v1.2.16` and push the tag.

## Detailed proposed workflow modifications:
See the detailed plan in the artifact: [implementation_plan.md](file:///C:/Users/Lenovo/.gemini/antigravity-ide/brain/25c4439c-4a81-4453-99e7-f8e7fa0dc347/implementation_plan.md)
