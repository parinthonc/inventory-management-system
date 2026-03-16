# Changelog: Fix Ledger Auto-Sync Not Detecting Z:\ Changes

**Date:** 2026-03-16  
**Issue:** Ledger auto-sync required manual refresh — file changes on Z:\ network share were not being detected automatically.

## Root Cause

The file watcher uses `_get_file_sizes()` to poll Z:\ source files every 30 seconds. However, Windows aggressively caches SMB/network drive metadata, so `os.stat()` returns **stale file sizes** for minutes at a time.

The sibling function `_get_file_mtimes()` already had a fix for this: calling `os.listdir()` on the parent directory before `os.stat()`, which forces Windows to refresh cached attributes. But `_get_file_sizes()` was **missing this cache-busting step** — so the watcher kept seeing the old file size and never triggered a sync.

## Fix

Added the same SMB cache-busting pattern to `_get_file_sizes()`:

```python
# Bust the Windows SMB metadata cache by listing parent directories first
busted_dirs = set()
for fpath in SERVER_SOURCE_FILES.get(source_key, []):
    parent = os.path.dirname(fpath)
    if parent not in busted_dirs:
        try:
            os.listdir(parent)  # Forces Windows to refresh cached attrs
        except OSError:
            pass
        busted_dirs.add(parent)
```

## Files Changed

| File | Change |
|------|--------|
| `server.py` | Added SMB cache busting to `_get_file_sizes()` (line ~877) |

## Impact

All four auto-sync sources (master, ledger, customer, invoice) benefit from this fix, as they all rely on `_get_file_sizes()` for change detection.
