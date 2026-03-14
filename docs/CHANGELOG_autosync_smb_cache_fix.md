# Fix: Auto-Sync Delayed on Network Drive (SMB Cache)

**Date:** 2026-03-13
**File:** `server.py` — `_get_file_mtimes()` function

## Problem

Auto-sync was detecting file changes on `Z:\` (network/SMB drive) with significant delays — sometimes minutes after the actual file modification. The webapp would not update even though the ERP had already written new data.

## Root Cause

Windows **caches SMB/CIFS directory metadata** aggressively for network shares. When Python calls `os.path.getmtime()` on a file like `Z:\DATA.CTOTAL\CVINDTR1`, Windows often returns a **stale cached timestamp** instead of querying the file server for the actual current value. This cache can persist for 10+ seconds to several minutes depending on Windows SMB settings.

The file watcher loop was polling every 30 seconds using `os.path.getmtime()`, but because of the stale cache, it would compare identical (cached) timestamps across multiple polling cycles and conclude "no change" — even though the file had been modified.

## Fix

Modified `_get_file_mtimes()` to **bust the Windows SMB metadata cache** before reading file timestamps:

1. **`os.listdir(parent_directory)`** — Listing the parent directory forces Windows to re-query the file server for fresh directory attributes, invalidating the local metadata cache.
2. **`os.stat(fpath)`** — Used instead of `os.path.getmtime()` for a more direct stat call after the cache has been refreshed.

### Before
```python
def _get_file_mtimes(source_key):
    mtimes = {}
    for fpath in SERVER_SOURCE_FILES.get(source_key, []):
        try:
            if os.path.exists(fpath):
                mtimes[fpath] = os.path.getmtime(fpath)
        except OSError:
            pass
    return mtimes
```

### After
```python
def _get_file_mtimes(source_key):
    mtimes = {}
    busted_dirs = set()
    for fpath in SERVER_SOURCE_FILES.get(source_key, []):
        parent = os.path.dirname(fpath)
        if parent not in busted_dirs:
            try:
                os.listdir(parent)  # Forces Windows to refresh cached attrs
            except OSError:
                pass
            busted_dirs.add(parent)
    for fpath in SERVER_SOURCE_FILES.get(source_key, []):
        try:
            st = os.stat(fpath)
            mtimes[fpath] = st.st_mtime
        except OSError:
            pass
    return mtimes
```

## Impact

- Auto-sync should now detect file changes within the standard 30-second polling interval
- Previously, detection could be delayed by several minutes due to Windows SMB caching
- No performance concern: `os.listdir()` is called once per unique parent directory per check cycle
