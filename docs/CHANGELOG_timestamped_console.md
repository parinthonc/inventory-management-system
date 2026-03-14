# Changelog: Timestamped Console Output

**Date**: 2026-03-14  
**File Modified**: `server.py`

## Summary

Added automatic timestamps to all console `print()` output in the server.

## What Changed

- Added a global override of Python's built-in `print()` function at the top of `server.py` (after imports, before any other code runs).
- Every `print()` call now automatically prepends `[HH:MM:SS]` (24-hour format) to the output.
- **No individual print statements were modified** — the override applies globally via `builtins.print`.

## How It Works

```python
import builtins

_original_print = builtins.print

def _timestamped_print(*args, **kwargs):
    timestamp = datetime.datetime.now().strftime('[%H:%M:%S]')
    _original_print(timestamp, *args, **kwargs)

builtins.print = _timestamped_print
```

## Example Output

**Before:**
```
[AutoSync] File watcher started. Checking every 30 seconds.
[AutoSync] Restored 5 detection time(s) from DB for today (2026-03-14)
```

**After:**
```
[14:37:04] [AutoSync] File watcher started. Checking every 30 seconds.
[14:37:04] [AutoSync] Restored 5 detection time(s) from DB for today (2026-03-14)
```

## Scope

- Affects all 86 `print()` calls in `server.py`
- Also affects `print()` calls in imported modules (e.g. `build_db.py`) when they run within the server process
- Does **not** affect subprocess scripts (e.g. extraction scripts run via `subprocess.run()`) since they run in separate Python processes

## Notes for AI/Developers

- The original `print` is preserved as `_original_print` if you ever need to output something without a timestamp.
- The override is placed **after** `import datetime` (line 10) since it depends on it, and **before** the Flask app creation.
