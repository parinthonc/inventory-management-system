# CHANGELOG: Auto-Sync Multi-User Toggle Fix

**Date:** 2026-03-12  
**Issue:** When multiple users access the web app, one user toggling auto-sync ON could be silently overridden by another user opening the page (whose browser defaults to all-OFF).

---

## Problem

The auto-sync toggle system had a **last-writer-wins** race condition:

1. Every browser tab pushed its `localStorage` toggle states to the server **on page load** and **on SSE reconnect**.
2. A new user (or a new tab with default-OFF `localStorage`) would silently overwrite another user's ON settings.
3. This meant auto-sync could be turned off without anyone explicitly doing so.

### Worst Case Scenario
User A enables ledger auto-sync → User B opens the app for the first time → B's browser pushes `{all: false}` to server → A's auto-sync is killed silently.

---

## Solution: Server as Single Source of Truth

### Client-side changes (`app.js`)

1. **Removed `syncConfigToServer(initialStates)` on page load** (was line 2942)
   - Previously: Client loaded localStorage and pushed to server immediately.
   - Now: Client loads localStorage only for initial UI display; waits for SSE `init` to get the server's actual state.

2. **Removed `syncConfigToServer(loadToggleStates())` on SSE reconnect** (was line 3097)
   - Previously: On reconnect, re-pushed localStorage to server.
   - Now: Waits for the `init` SSE message which contains the server's current state.

3. **Kept**: `onToggleChange()` still pushes to server — only when a user **explicitly clicks** a toggle.

4. **Kept**: SSE `config_update` handler still updates localStorage and UI — so all tabs stay in sync.

### Server-side changes (`server.py`)

1. **Added `sync_config.json` persistence** — Toggle states are saved to disk whenever changed, so they survive server restarts.
2. **Added `_load_sync_config()` / `_save_sync_config()`** — Read/write toggle states from `sync_config.json`.
3. **`_sync_enabled` initialized from file** instead of hardcoded `False`.

---

## Data Flow (After Fix)

```
Page Load:
  Browser → reads localStorage (for quick UI display only)
  SSE init → server sends its current toggle state → browser updates localStorage + UI

User Clicks Toggle:
  Browser → POST /api/sync/config → server updates _sync_enabled
  Server → saves to sync_config.json
  Server → broadcasts 'config_update' via SSE → all other browsers update

Server Restart:
  Server → reads sync_config.json → restores last toggle states
```

## Files Modified

| File | Change |
|------|--------|
| `app.js` | Removed 2 lines that pushed localStorage to server on load/reconnect |
| `server.py` | Added `sync_config.json` persistence for toggle states |
