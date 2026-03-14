# CHANGELOG: Restore Detection Times on Server Restart (2026-03-14)

## Problem
When the server was stopped and restarted, all "ตรวจพบเมื่อ HH:MM" (detected at)
tags disappeared, even though the transactions were detected earlier the same day.

### Root Cause
Detection times are stored in two places:
1. **In-memory** (`_last_sync_changes['detection_times']`) — used by the
   `/api/sync/changes` API endpoint, which the frontend fetches on page load
2. **In the database** (`csv_last_sold_detected_at` column in `products` table)
   — persisted during each sync

When the server restarts, the in-memory dictionary is initialized empty.
The frontend calls `/api/sync/changes`, gets empty data, and shows no
detection time tags — even though the DB still has all the timestamps.

## Solution
Added `_restore_detection_times()` function in `server.py` that runs at
startup and:
1. Queries the `products` table for all rows where
   `csv_last_sold_detected_at` starts with today's date
2. Extracts the HH:MM portion from each timestamp
3. Populates `_last_sync_changes['detection_times']` and
   `_last_sync_changes['changed_product_skus']` so the frontend
   receives correct data from `/api/sync/changes`

### Files Changed
- **`server.py`** — Added `_restore_detection_times()` function (called at
  module load time, after `_last_sync_changes` initialization)

## Behavior Now
- Server restart **no longer loses** today's detection times
- All "ตรวจพบเมื่อ HH:MM" tags that were recorded before the restart
  are immediately visible after restart
- New syncs after restart continue to merge detection times as before
- Detection times still reset automatically when the day rolls over
