# Changelog: Size-Based File Change Detection

**Date:** 2026-03-14  
**Fix:** Eliminate phantom auto-sync triggers caused by ERP touching files without data changes

## Problem

The auto-sync file watcher used `os.stat().st_mtime` (file modification timestamp) to detect
changes in the ERP source files on `Z:\DATA.CTOTAL`. However, the ERP software frequently
"touches" these files — updating their timestamp — without actually modifying the data content.

This caused **phantom sync triggers**: the system would run a full extraction + reload cycle
(taking minutes), only to find zero actual changes. This wastes time, CPU, and network I/O
to the file server.

### Common causes of mtime-only changes:
- ERP flushing in-memory caches (rewriting identical data)
- ERP rebuilding B-tree indexes for optimization
- SMB/network drive reconnection updating metadata
- Antivirus or backup software scanning files
- ERP opening files in read-write mode (Windows updates mtime on close)

## Solution: Check File Size Instead of Timestamp

Switched the file watcher from comparing `st_mtime` to comparing `st_size`.

**Why this works:**
- Real ERP changes (new transactions, deletions) **always** change file size because records are appended or removed
- ERP "touching" files without data changes **never** changes file size
- `os.stat()` returns both `st_mtime` and `st_size` in the same call — **zero additional server load**

**Edge case:** If the ERP modifies an existing record's value (e.g., editing a quantity) without
adding/removing records, the size stays the same and the change would be missed. In practice,
this is extremely rare — ERP data files almost always grow when real changes occur.

### Files Changed

| File | Changes |
|------|---------|
| `server.py` | Added `_get_file_sizes()` function; changed `_sync_state` keys from `last_mtime` to `last_size`; updated `_file_watcher_loop()` and `_run_sync_task()` to compare sizes instead of timestamps |

### What Was NOT Changed

- **`_get_file_mtimes()`** — kept as-is, still used by `_check_startup_staleness()` which compares
  Z: source timestamps against local output CSVs (a different use case that genuinely needs mtime)
- **`_check_startup_staleness()`** — unchanged, still uses mtime to detect if local data is
  older than server data on startup

### Log Output Change

Before:
```
[AutoSync] Change detected in CVINDTR1 for ledger
```

After:
```
[AutoSync] Size changed in CVINDTR1 for ledger: 15728640 -> 15729152
```

The new log message shows the old and new file sizes in bytes, making it easy to verify
that a real change occurred.
