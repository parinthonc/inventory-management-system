# CHANGELOG: Watcher Debug Toggle + Console Tag Fix
**Date**: 2026-03-16

## Summary
Added a debug toggle in the admin panel to control verbose file watcher console output, and fixed misleading `[AutoSync]` tags when sync is manually triggered.

## Changes

### server.py
- **`_watcher_debug` global flag**: Loaded from and saved to `sync_config.json`. When `True`, the file watcher loop prints detailed status for every check cycle (size changes, "no change", skipped sync).
- **`_run_sync_task(source_key, trigger='auto')`**: New `trigger` parameter controls the console log tag:
  - `'auto'` → `[AutoSync]` (file watcher detected changes)
  - `'manual'` → `[ManualSync]` (user clicked a Refresh button)
  - `'startup'` → `[StartupSync]` (startup staleness check)
- **`/api/sync/config` GET/POST**: Now includes `watcher_debug` field (no new routes).
- **`_save_sync_config()`**: Persists `watcher_debug` alongside per-source toggles.
- Verbose watcher prints (size checks, "no change", "skipped") gated behind `_watcher_debug`.
- Critical prints (sync results, errors, disappeared transactions) always output regardless.

### index.html
- Added "Watcher Debug Log" toggle in the admin panel modal, below Database Backups section.
- Uses the same `backup-toggle` CSS class for consistent styling.

### app.js
- Added `_loadWatcherDebugState()` function to load initial toggle state from `/api/sync/config`.
- Added change handler for `#watcher-debug-toggle` that POSTs to `/api/sync/config`.
- Fixed frontend `console.log` tags from `[AutoSync]` to `[Sync]` (neutral tag).

### sync_config.json
- Added `"watcher_debug": false` field. Existing keys unchanged.
