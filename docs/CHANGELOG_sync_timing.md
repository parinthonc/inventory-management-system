# Changelog: Sync Duration Timing in Console

**Date:** 2026-03-13  
**File Modified:** `server.py`

## What Changed

Added elapsed time measurement to sync operations (both auto-sync and manual sync).
When a sync finishes, the console now prints the time taken in minutes and seconds.

### Console Output Examples

**Success:**
```
[AutoSync] master sync completed successfully. (Time: 0m 12.3s)
[AutoSync] ledger sync completed successfully. (Time: 1m 45.2s)
```

**Failure:**
```
[AutoSync] invoice sync failed: Script failed: ... (Time: 0m 3.1s)
```

## Implementation Details

- A `sync_start_time = time.time()` call is recorded right before the `try` block in `_run_sync_task()`.
- On completion (success or error), the elapsed time is calculated and formatted as `Xm Y.Zs`.
- Both auto-sync (triggered by file watcher) and manual sync (via `/api/sync/trigger/<source>`) go through the same `_run_sync_task()` function, so both are covered.

## Resource Impact

**Negligible.** `time.time()` is a trivial system clock read (nanoseconds). The subtraction and formatting are equally free. No additional threads, no I/O, no memory allocations worth mentioning.

## Lines Changed

| Location | Change |
|---|---|
| `server.py:186` | Added `sync_start_time = time.time()` |
| `server.py:313-316` | Print elapsed time on success |
| `server.py:321-324` | Print elapsed time on failure |
