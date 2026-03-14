# CHANGELOG: Persistent Detection Tags (2026-03-13)

## Problem
The "ตรวจพบเมื่อ" (detected at) tag disappeared after subsequent syncs. When a
new sync ran, the detection times from previous syncs were completely replaced,
causing earlier detections to lose their timestamps.

## Solution
Both server and frontend now **merge** detection times across all syncs
throughout the current day, instead of replacing them:

### `server.py` — Merge logic in `_run_sync_task()`
- Before: `_last_sync_changes.update(changes)` — replaces all detection_times
- After: Checks if the previous sync was from the same day; if so, merges the
  previous detection_times into the new ones before updating. When the day
  rolls over, detection times start fresh automatically.

### `app.js` — SSE sync handler (line ~3095)
- Before: `state.syncDetectionTimes = new Map(Object.entries(detTimes))` — replaces
- After: Iterates over new detections and adds them to the existing Map using
  `.set()`, preserving all earlier detections from the same browser session.

## Behavior Now
- Every product detected as updated during any sync **today** keeps its
  "ตรวจพบเมื่อ HH:MM" tag visible for the rest of the day
- If the same product is detected again in a later sync, the time updates to
  the latest detection
- Detection times automatically reset the next day
