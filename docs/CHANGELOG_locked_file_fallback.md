# CHANGELOG: Network Drive & Locked File Fixes for Mini PC

**Date:** 2026-03-14  
**Files:** `python script/extract_stock_ledger_v4.py`, `server.py`

## Problem

On the mini PC, two issues prevent reliable ledger sync:

1. **Disconnected network drive:** Windows automatically drops idle mapped network drives after ~15 min. The `Z:` drive mapping still shows up but the connection is dead. Clicking `Z:\` in File Explorer reconnects it — but AutoSync runs without user interaction.
2. **File locked by Express:** Even when the drive is connected, the accounting software may hold an exclusive lock on the data files.
3. **Stale data after deploy:** When copying the project folder to the mini PC, local CSVs may be hours/days old. AutoSync only triggers on *changes* to Z: files, not on startup staleness — so the webapp shows stale data until the next sale.

## Fixes

### `extract_stock_ledger_v4.py`

#### 1. `_ensure_network_drive(path)` — reconnects idle drives (NEW)

Called at script startup before any file access:
- Tries `os.listdir()` on the drive root to trigger Windows reconnection
- If that fails, runs `net use Z:` to force reconnect
- Exits early with clear error if drive is unreachable

#### 2. `_read_file_with_retry()` — faster retries + copy fallback

- **Reduced retries:** 3 attempts with 3s/6s/12s delays (21s total vs 155s)
- **Added `_copy_locked_file()` fallback:** After direct reads fail, uses `cmd /c copy /B` to copy the locked file to a temp directory, reads from the copy, then cleans up

#### 3. `_copy_locked_file(filepath)` (NEW)

- Creates temp directory, copies file via subprocess, reads copy, cleans up
- Returns `None` on failure (so caller can raise the original error)
- 30-second timeout on the copy command

### `server.py`

#### 4. `_check_startup_staleness()` — auto-sync on startup (NEW)

Called in `_file_watcher_loop()` right after initializing baseline mtimes:
- Compares Z: source file timestamps against local output CSV timestamps
- If Z: files are newer (or local CSVs are missing), triggers sync for that source
- Only runs for sources that have auto-sync **enabled**
- Staggers sync launches by 1 second to avoid overloading

Output files checked per source:
| Source | Local CSV |
|---|---|
| master | `product master table/product_master_active.csv` |
| ledger | `ledger/stock_ledger_full.csv` (and `.csv.new`) |
| customer | `customer master table/customer_master.csv` |
| invoice | `invoice/invoice_headers.csv` |

## New imports (extract_stock_ledger_v4.py)

- `tempfile` — for creating temp directories
- `subprocess` — for running `cmd /c copy` and `net use`
