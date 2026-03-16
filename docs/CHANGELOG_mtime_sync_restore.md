# Changelog: Switch Auto-Sync Back to Mtime-Based Detection

**Date:** 2026-03-16  
**Change:** Revert from size-based to mtime-based file change detection for auto-sync

## Why

Size-based detection (introduced 2026-03-14) eliminated phantom syncs from ERP "touching" files,
but it missed **in-place record modifications** where the ERP edits existing data without changing
file size. This caused auto-sync to never trigger for ledger updates — only manual sync worked.

## Tradeoff

Mtime-based detection catches ALL changes (including in-place edits), but may also trigger
phantom syncs when the ERP touches files without meaningful data changes. This is an acceptable
tradeoff for now — reliability of detecting real changes is more important than avoiding
occasional unnecessary syncs.

## Files Changed

| File | Change |
|------|--------|
| `server.py` | `_file_watcher_loop()`: switched from `_get_file_sizes()` to `_get_file_mtimes()` |
| `server.py` | `_sync_state`: renamed `last_size` → `last_mtime` in all 4 source entries |
| `server.py` | `_run_sync_task()`: post-sync state update now saves mtimes instead of sizes |

## Debug Output Change

Before (size-based):
```
[AutoSync] Size changed in CVINDTR1 for ledger: 15728640 -> 15729152
```

After (mtime-based):
```
[AutoSync] Mtime changed in CVINDTR1 for ledger: 1710556800.0 -> 1710556830.0
```
