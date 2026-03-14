# Changelog: Waitress Production Mode Support

**Date:** 2026-03-13  
**Purpose:** Add production-grade WSGI server (Waitress) while keeping Flask dev server for development

---

## Problem

The server was running Flask's built-in development server (`app.run(debug=True)`) in all environments, including the mini PC used for production. This is:
- Single-threaded (one request at a time)
- Not optimized for stability or performance
- Exposes debug info (security risk)

## Solution: Dual-Mode Server

### How it works

| Mode | Command | Server | Debug | Threads |
|---|---|---|---|---|
| **Development** | `python server.py` | Flask dev server | ✅ Yes | 1 |
| **Production** | `python server.py --production` | Waitress | ❌ No | 16 (default) |

### Files Modified

#### `server.py` (lines 1875+)
- Added `argparse` for CLI flags: `--production`, `--port`, `--threads`
- Default behavior (no flags) = Flask dev server (unchanged from before)
- `--production` flag = uses Waitress with 16 threads
- Graceful fallback: if Waitress is not installed, prints error and falls back to Flask

#### `start_server.bat`
- Runs `python server.py --production` (Waitress mode)
- Auto-installs Waitress if not found on the mini PC
- This is the file used on the mini PC to start the server

### CLI Options

```
python server.py                          # Dev mode (Flask, debug=True)
python server.py --production             # Production mode (Waitress, 16 threads)
python server.py --production --port 9090 # Custom port
python server.py --production --threads 8 # Custom thread count
```

### Dependencies

- `waitress` (installed via `pip install waitress`) — only needed on the mini PC
- Pure Python, no C extensions, works natively on Windows

### Why 32 threads?

The mini PC has 8 cores. The app uses SSE (Server-Sent Events) at `/api/sync/events` — each
browser tab holds one thread for the SSE connection. With 32 threads, the server can handle
~25 concurrent users while leaving threads free for API requests.

### PEP 3333 Fix: `Connection` header removed

The SSE endpoint previously included a `Connection: keep-alive` response header. This is a
**hop-by-hop header** that WSGI applications are not allowed to set (per PEP 3333). Flask's
dev server was lenient about this, but Waitress enforces it strictly and throws an
`AssertionError`. The fix was to simply remove the header — Waitress manages connection
persistence on its own.
