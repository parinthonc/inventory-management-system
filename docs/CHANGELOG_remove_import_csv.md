# Changelog: Remove Import CSV Feature

**Date:** 2026-03-15

## Summary
Removed the "Import CSV" button and all associated code. This feature allowed manually importing pre-built CSV files from a folder path, but became redundant after the auto-sync system with per-source Refresh buttons was implemented.

## What Was Removed

| File | What | Lines Removed |
|---|---|---|
| `index.html` | Import CSV button (navbar) + modal dialog | ~44 lines |
| `app.js` | DOM refs, event listeners, `importCsvFromFolder()` | ~120 lines |
| `index.css` | Light theme override, `.import-csv-dialog`, responsive rule | ~12 lines |
| `server.py` | `_CSV_IMPORT_MAP` dict + `/api/import-csv-folder` endpoint | ~97 lines |

## Why
The 4 Refresh buttons (Master, Ledger, Invoice, Customer) each trigger `/api/sync/trigger/<source>` which runs extraction scripts AND reloads caches — strictly more powerful than Import CSV which only copied files and reloaded caches. The auto-sync system also handles this automatically on a timer.

## Leftover
- `localStorage` key `importCsvLastPath` may remain in users' browsers but is harmless and will not be written to again.
