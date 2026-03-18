# Phantom Sync Cooldown

**Date:** 2026-03-18

**Purpose:** Prevent wasteful autosync cycles when the ERP touches source files without changing actual data. After N consecutive autosyncs detect zero real changes, impose a configurable cooldown period during which autosync is suppressed.

## How It Works

1. The file watcher detects a file change (mtime/size) and triggers `_run_sync_task`
2. After extraction + cache reload, the diff engine finds 0 changed products, 0 new moves, 0 disappeared transactions
3. The **phantom streak counter** increments for that source
4. When streak reaches the **threshold** (default: 3), cooldown activates for that source  
5. During cooldown, file changes are still detected but sync is **skipped** (mtime is updated so changes don't pile up)
6. After the cooldown expires, syncing resumes normally
7. **Manual syncs** and **startup syncs** always run and reset the streak

## Configuration

Both settings are adjustable in the **Admin Panel → Phantom Sync Cooldown** section:

| Setting | Default | Range | Description |
|---------|---------|-------|-------------|
| No-change syncs before cooldown | 3 | 1–50 | Consecutive autosyncs with 0 real changes before cooldown activates |
| Cooldown duration (seconds) | 120 | 10–3600 | How long to suppress autosync after threshold is reached |

Settings are persisted in `sync_config.json` (keys: `cooldown_threshold`, `cooldown_seconds`).

## Changes

### `server.py`
- `_load_sync_config()` / `_save_sync_config()`: persist `cooldown_threshold` and `cooldown_seconds`
- New state: `_phantom_streak` and `_cooldown_until` dicts (per-source)
- `_file_watcher_loop()`: added cooldown check before triggering sync
- `_run_sync_task()`: tracks no-change autosyncs, activates cooldown at threshold, resets on real changes or manual/startup sync
- `GET /api/sync/config`: returns cooldown settings + current cooldown state
- `POST /api/sync/config`: accepts `cooldown_threshold` and `cooldown_seconds`

### `index.html`
- Added "Phantom Sync Cooldown" section in admin panel with two number inputs

### `app.js`
- `_loadWatcherDebugState()`: also loads and populates cooldown inputs
- `_setupAdminHandlers()`: added debounced change handlers for cooldown inputs

## Console Output Examples

```
[AutoSync] No real data changes — phantom streak: 1/3
[AutoSync] No real data changes — phantom streak: 2/3
[AutoSync] No real data changes — phantom streak: 3/3
[AutoSync] ⏸️  Cooldown activated for ledger — 2m 0s (after 3 consecutive no-change syncs)
[AutoSync] ledger in cooldown (95s remaining) — skipped
[AutoSync] Real changes found — phantom streak reset (was 2)
[ManualSync] manual sync — phantom streak reset
```
