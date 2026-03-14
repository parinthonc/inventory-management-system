# Fix: Auto-Sync Toggling All Sources Instead of Only Enabled Ones

**Date:** 2026-03-12  
**Issue:** When only the "Ledger" auto-sync toggle was turned ON, other sources (Master, Invoice) were also auto-syncing.

## Root Cause

The **server needed to be restarted** to pick up the toggle toggle code.

The per-source auto-sync toggle feature was added to the code in a previous session (conversation `28c336b6`), which added:
- `_sync_enabled` dict in `server.py` (defaults all to `False`)
- `POST /api/sync/config` endpoint to update toggle states
- `GET /api/sync/config` endpoint to read toggle states
- Toggle check in `_file_watcher_loop()` (lines 307-311) to skip auto-sync for disabled sources
- Frontend toggle UI and `syncConfigToServer()` in `app.js`

However, the running server instance had been started **before** these changes were committed. The running server:
1. **Did not have** the `/api/sync/config` endpoints (confirmed: returned `404 Not Found`)
2. **Did not have** the `_sync_enabled` check in `_file_watcher_loop()` — so all sources auto-synced when file changes were detected
3. Frontend toggle state was saved to `localStorage` but the `POST /api/sync/config` call silently failed (405/404)

### Evidence
- `GET /api/sync/config` → `404 Not Found` (on old running server)
- `GET /api/sync/status` → showed `last_sync` timestamps for master, ledger, AND invoice even though only ledger toggle was ON

## Fix Applied

**Restarted the server** (`python server.py`) so it runs the latest code with:
- Working `/api/sync/config` GET/POST endpoints
- `_sync_enabled` check in `_file_watcher_loop()` that skips auto-sync for disabled sources
- Proper toggle state synchronization between frontend and backend

### Post-fix verification:
```
GET /api/sync/config → {"customer": false, "invoice": false, "ledger": true, "master": false}
POST /api/sync/config {"ledger": true} → {"success": true, "changed": ["ledger"], ...}
```

## Affected Files
- No code changes needed — the code on disk was already correct
- Only action: server restart to run updated code
