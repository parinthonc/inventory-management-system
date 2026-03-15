# CHANGELOG: Sync Change Highlighting (2026-03-12)

## Summary
Added visual highlighting to distinguish **newly detected** products and stock moves after
a sync (auto-sync or manual trigger). Rows that are new or changed show a green glow
animation and a **"อัปเดต"** badge next to the part code. The highlight **persists** until the
next sync detects new changes.

For items sold **today**, the detection time is also shown (e.g. "ตรวจพบเมื่อ 14:35") in the
"วันที่ขายล่าสุด" column.

## Motivation
When auto-sync detects changes on the ERP server and refreshes data, the table silently
updates. Users could not tell which items were added or changed. This feature makes new
entries immediately obvious at a glance.

## Changes

### `index.css`
- Added `@keyframes sync-pulse` — subtle border color pulse animation (infinite, not fade-out)
- Added `.sync-new-row` class — green left-border accent + static green background + pulse
- Added `.sync-badge` class — small green pill badge for the "อัปเดต" label
- Added `.sync-detection-time` class — green text for "ตรวจพบเมื่อ HH:MM" display

### `app.js`
- Added state variables `syncNewProductSkus`, `syncNewMoveKeys` (Sets), and `syncDetectionTimes` (Map)
- Rewrote `onSyncDone(source)` with expanded snapshot/diff logic:
  1. Before re-fetching: snapshots `sku → last_sold_date` map and move fingerprints
  2. After re-fetching: detects both **new SKUs** and **last_sold_date changes**
  3. Records detection time for items sold today
  4. Highlights **persist** — only cleared when the next sync replaces them
  5. Also clears old highlights if next sync finds no new changes
- Modified `renderProducts()` — checks `syncNewProductSkus` for highlight class/badge,
  and shows detection time from `syncDetectionTimes` for today's sales
- Modified `renderMoves()` — checks `syncNewMoveKeys` for highlight class/badge

## How It Works
- Product diff uses `sku → last_sold_date` map (not just SKU presence)
- Move diff uses fingerprint key (`partcode|date|docref|qtyin|qtyout`)
- Highlights persist until next sync replaces them (no auto-fade timeout)
- Detection time uses `th-TH` locale formatting for consistency
- The first load after page refresh never highlights anything (avoids false positives)
- Only master and ledger syncs trigger highlighting (those are the relevant data sources)

### Server-Side Change Tracking (Update 2)
- **Change detection moved to server**: `_run_sync_task` now snapshots product
  `csv_last_sold_date` and today's moves BEFORE reload, computes diff AFTER reload.
- **`_last_sync_changes` global**: stores the latest diff in server memory, survives
  across client connections (but not server restarts).
- **`/api/sync/changes` endpoint**: new page loads fetch this to display highlights
  even if the user arrived after the sync completed.
- **SSE `sync_done` event** now includes `changes` payload, so connected tabs
  receive changes directly without local diff computation.
- **Frontend `loadSyncChanges()`**: called in `init()` to fetch server-stored changes
  on page load.

