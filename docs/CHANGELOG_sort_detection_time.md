# CHANGELOG: Sort by วันที่ขายล่าสุด with Detection Time Tiebreaker

**Date:** 2026-03-13

## Problem
When sorting by "วันที่ขายล่าสุด" (last sold date), all products sold on the same date (e.g., today) appeared in an arbitrary order. There was no way to distinguish which sales were detected earlier vs later in the day.

## Solution
Use the **ตรวจพบเมื่อ (detection time)** that is already recorded during sync as a secondary sort key, so products sold on the same date are further sorted by when they were detected.

### What Changed

#### 1. New DB Column: `csv_last_sold_detected_at`
- Added `csv_last_sold_detected_at TEXT` column to the `products` table
- Stores the full datetime string in `YYYY-MM-DD HH:MM` format (e.g., `2026-03-13 11:35`)
- This column is **NOT cleared** during ledger re-sync — it accumulates detection times throughout the day

#### 2. Detection Times Persisted to DB (`server.py` ~line 275)
- After computing the sync diff, the detection times are now written to the DB:
  ```python
  cursor.execute('UPDATE products SET csv_last_sold_detected_at = ? WHERE sku = ?', (det_full, det_sku))
  ```
- This allows SQL ORDER BY to use detection time as a tiebreaker

#### 3. Enhanced ORDER BY for `last_sold_date` Sort (`server.py` ~line 748)
- **Before:** `ORDER BY last_sold_date desc`
- **After:** `ORDER BY last_sold_date desc, p.csv_last_sold_detected_at desc`
- Products with the same sale date now sort by detection time (most recently detected first in DESC mode)

### How It Works
- ERP data (CVINDTRN) only stores dates in `DD/MM/YY` format — **no time-of-day info**
- The only time info available is the **ตรวจพบเมื่อ** tag, recorded when the server detects a new sale during auto-sync
- By storing this detection time in the DB alongside the sale date, SQL sort can use both

### Limitations
- Detection time is only available for sales detected during the current day's sync runs
- Older sales (before today) will not have detection times — they sort by date only, then arbitrarily among same-date items
- If the server restarts, detection times for today are preserved (stored in DB), but the in-memory `_last_sync_changes` dict resets
