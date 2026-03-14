# CHANGELOG: Real-Time Auto-Sync System

**Date:** 2026-03-12  
**Purpose:** Eliminate the need to manually press Refresh buttons and wait 3-4 minutes. The webapp now monitors Z:\ server files for changes and auto-updates in the background.

---

## Problem

Previously, updating data in the webapp required:
1. Clicking a "Refresh" button (Master/Ledger/Customer/Invoice)
2. Waiting 3-4 minutes while the server synchronously ran extraction scripts
3. The UI was completely blocked during this time

## Solution

### Architecture: Background File Watcher + SSE (Server-Sent Events)

```
Z:\ Server Files ──► File Watcher Thread ──► Extraction Scripts ──► Cache Reload
                         (every 30s)              (background)         │
                                                                       ▼
Web Browser ◄──────── SSE Stream ◄──────── Broadcast Events ◄──── Updated Data
  (auto-refresh)     (real-time)          (sync_start/done)
```

### How It Works

1. **Background File Watcher** (`_file_watcher_loop` in `server.py`):
   - Runs in a daemon thread, checking Z:\ source files every 30 seconds
   - Compares file modification times (`os.path.getmtime()`) against last known values
   - When a change is detected, triggers extraction in a separate background thread
   - Never blocks the Flask HTTP server

2. **Non-Blocking Extraction** (`_run_sync_task`):
   - Runs the appropriate extraction script (`extract_product_master.py`, `extract_stock_ledger_v4.py`, etc.)
   - Reloads in-memory caches after extraction completes
   - Broadcasts progress events to all connected browsers via SSE

3. **Server-Sent Events** (`/api/sync/events`):
   - Persistent HTTP connection from browser to server
   - Server pushes real-time status updates: `sync_start`, `sync_progress`, `sync_done`, `sync_error`
   - Auto-reconnects on connection loss (5s retry)

4. **Frontend Auto-Refresh** (`initAutoSync()` in `app.js`):
   - Listens to SSE stream
   - When `sync_done` is received, automatically calls `fetchProducts()`, `fetchMoves()`, etc.
   - Updates visual indicators in the sync status bar

---

## Files Changed

### `server.py`
- **Added imports**: `threading`, `time`, `queue`, `Response` from Flask
- **Added `SERVER_SOURCE_FILES`**: Maps each data source to its Z:\ binary files
  - `master` → CVINDMAS, CVINDMA1, CVINDBRA (from DATA.CTOTAL)
  - `ledger` → CVINDTR1, CVINDTRN, CVINDMAS (from DATA.CTOTAL)
  - `customer` → CVARDMAS (from DATA.CW)
  - `invoice` → CVIVDMAS, CVIVDTRN (from DATA.CW)
- **Added background sync system**:
  - `_file_watcher_loop()` — daemon thread monitoring file mtimes
  - `_run_sync_task()` — runs extraction + cache reload in background
  - `_reload_master_from_csv()` — shared logic for master DB rebuild
  - `_broadcast_sync_event()` — pushes events to SSE subscribers
  - `start_file_watcher()` — starts the watcher thread
- **Added API endpoints**:
  - `GET /api/sync/events` — SSE stream for real-time sync status
  - `GET /api/sync/status` — JSON snapshot of all sync states
  - `POST /api/sync/trigger/<source_key>` — manually trigger background sync
- **Updated `__main__`**: starts file watcher, uses `use_reloader=False`

### `app.js`
- **Updated refresh buttons** (Master, Ledger, Customer, Invoice):
  - Changed from blocking synchronous `fetch('/api/refresh-*')` calls
  - Now uses non-blocking `fetch('/api/sync/trigger/*')` — returns instantly
  - Removed confirmation dialogs and inline loading states (handled by sync bar)
- **Added `initAutoSync()` IIFE**:
  - Connects to `/api/sync/events` SSE stream
  - Updates sync status bar dots and labels in real-time
  - Auto-refreshes data views when sync completes
  - Click-to-sync on status bar items for manual triggers
  - Auto-reconnects SSE on connection loss

### `index.html`
- **Added sync status bar** at bottom of page:
  - Shows overall sync status (Monitoring / Updating / Error)
  - Individual dots for Master, Ledger, Customer, Invoice
  - Progress text showing current operation
  - Clickable items for manual sync trigger

### `index.css`
- **Added `.sync-status-bar` styles**:
  - Fixed position at bottom of viewport
  - Glassmorphism effect matching existing design
  - Animated pulsing dots for syncing state
  - Color-coded states: gray (idle), blue (syncing), green (done), red (error)
  - Updated `.main-content` padding to prevent overlap

---

## Configuration

| Setting | Value | Location |
|---------|-------|----------|
| File check interval | 30 seconds | `FILE_CHECK_INTERVAL` in `server.py` |
| Extraction timeout | 600 seconds | `timeout=600` in `_run_sync_task()` |
| SSE heartbeat | 30 seconds | `q.get(timeout=30)` in SSE generator |
| SSE reconnect | 5 seconds | `setTimeout(connectSSE, 5000)` in `app.js` |
| Sync done display | 5 seconds | `setTimeout(... 5000)` reset to idle |
| Sync error display | 10 seconds | `setTimeout(... 10000)` reset to idle |

---

## User Experience

### Before
- Click "Refresh Ledger" → page freezes for 3-4 minutes → alert popup → data updates

### After
- **Automatic**: Data updates automatically when someone uses the ERP system on Z:\
- **Non-blocking**: Click refresh button → returns instantly, sync runs in background
- **Visual feedback**: Bottom status bar shows live progress with animated dots
- **Manual override**: Click any item in the status bar to force a sync
- **Always monitoring**: Gray dot = watching, Blue pulsing dot = syncing, Green = done

---

## Notes for AI/Human

- The old `/api/refresh-*` endpoints still exist and work (backward compatible)
- The new `/api/sync/trigger/*` endpoints are non-blocking wrappers
- If Z:\ drive is unreachable, the file watcher gracefully handles errors
- `use_reloader=False` prevents Flask's auto-reloader from spawning duplicate watcher threads
- SSE uses `queue.Queue` per client with maxsize=100 to prevent memory leaks

---

## Update: Per-Source Toggle Switches (2026-03-12)

Added individual on/off toggle switches for each data source in the footer status bar.

### How it works
- Each source (Master, Ledger, Customer, Invoice) has a small toggle switch
- **OFF** (default): File watcher still monitors Z:\ timestamps (lightweight), but does NOT trigger extraction when changes detected. The dot/label appear dimmed.
- **ON**: When Z:\ file changes are detected, extraction runs automatically in the background
- **Manual sync always works**: Clicking the dot/label or navbar Refresh button triggers sync regardless of toggle state
- Toggle state is saved in localStorage (persists across page reloads) and synced to the server via `POST /api/sync/config`
- Multiple browser tabs stay in sync via SSE `config_update` events

### Server changes
- Added `_sync_enabled` dict — controls which sources auto-extract on file change
- Added `GET /api/sync/config` — returns current toggle states  
- Added `POST /api/sync/config` — updates toggle states, broadcasts to SSE clients
- File watcher checks `_sync_enabled[source]` before triggering extraction
- When auto-sync is OFF, file mtimes are still updated silently (avoids triggering extraction for old changes when re-enabled)

### Frontend changes
- Added toggle switch checkboxes (`<label class="sync-toggle">`) next to each sync item
- Toggle CSS: compact iOS-style slider, blue glow when ON
- `disabled` class dims the dot/label when auto-sync is OFF
- Overall label shows count: "Auto-Sync (2/4)" when 2 of 4 enabled
- Click-to-sync now only triggers on dot/label click, not on toggle click (via `stopPropagation`)
