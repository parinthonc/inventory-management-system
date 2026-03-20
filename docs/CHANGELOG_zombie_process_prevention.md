# Zombie Process Prevention — Audit & Fix

**Date:** 2026-03-20

## Summary

Audited `server.py` for zombie/orphan process risks. The codebase is already well-protected
because all subprocess calls use `subprocess.run()` (which blocks and auto-reaps) and all
background threads are set to `daemon=True`.

## Finding: Missing Timeout on Ledger Refresh

The `/api/refresh-ledger` endpoint (line ~3102) was the **only** `subprocess.run()` call
without a `timeout` parameter. If the extraction script ever hung, the Flask request thread
would be stuck forever (not a "zombie" per se, but a stuck thread that would never be freed).

### Fix Applied

1. Added `timeout=600` (10 minutes) to the `subprocess.run()` call in `refresh_ledger()`
2. Added `subprocess.TimeoutExpired` exception handler, consistent with all other refresh endpoints

### Before
```python
result = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
```

### After
```python
result = subprocess.run([sys.executable, script_path], capture_output=True, text=True, timeout=600)
```

Plus explicit timeout error handling:
```python
except subprocess.TimeoutExpired:
    return jsonify({'success': False, 'message': 'Script timed out after 10 minutes'}), 500
```

## Existing Protections (Already in Place)

| Pattern | Where | Why It's Safe |
|---|---|---|
| `subprocess.run()` with `timeout` | `/api/sync`, `/api/refresh-*` | Blocks, reaps child, kills on timeout |
| `threading.Timer(..., daemon=True)` | Auto-backup scheduler | Killed when main process exits |
| `threading.Lock()` / `threading.RLock()` | Background sync system | Thread-safe, daemon threads |

## Key Takeaway

- **No `subprocess.Popen()` is used** anywhere in the server — so no risk of unreferenced child processes.
- **All threads are daemon threads** — they die automatically when the Flask server stops.
- The only gap was the missing timeout on the ledger refresh, which is now fixed.
