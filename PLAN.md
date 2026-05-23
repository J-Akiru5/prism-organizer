# PLAN: Auto-Update Checker System (Approved)

## Goal
Implement an auto-update checker for the CLI/TUI to notify users of new versions, with throttling to prevent startup lag.

## Approved Choices
1. **Update Behavior**: **Option A**
   - **NPM Users**: Show a notification banner on startup with the update command (`npm update -g prism-organizer`).
   - **Standalone Executable Users**: Show an interactive prompt to automatically download and replace the `.exe`.
2. **Throttling**: Check only once every 24 hours (caching the last check in `~/.prism-organizer/.last_update_check`) to avoid network latency.

For full implementation details, please see the artifact: [implementation_plan.md](file:///C:/Users/Lenovo/.gemini/antigravity-ide/brain/25c4439c-4a81-4453-99e7-f8e7fa0dc347/implementation_plan.md)
