# CHANGELOG: Active Thumbnail Refresh for Photo Flags Tab

**Date**: 2026-03-19
**Files Modified**: `server.py`

## Problem

The Photo Flags tab (📷 รายการที่ต้องถ่ายรูปเพิ่ม) displayed stale thumbnails from the `products` DB table.
Thumbnails could become outdated when images arrived via Z:\ file sync or other external means
(i.e. not through the web upload handler which already updates the DB).

## Solution

Added **active thumbnail refresh** — every time the photo flags tab is loaded, the server
re-computes thumbnails from disk for each flagged item and updates the DB if the value has changed.

### Changes in `server.py`

1. **New function `_refresh_photo_flag_thumbnails(items)`** (line ~3429)
   - Loops through each photo-flagged item
   - Calls `find_thumbnail(sku)` to get the current path from disk
   - If it differs from `products.thumbnail`, updates both the response item and the DB
   - Logs refreshed SKUs to the console

2. **Modified `get_photo_flags()`** — calls `_refresh_photo_flag_thumbnails(flags)` after fetching rows

3. **Modified `get_photo_flags_pickup()`** — calls `_refresh_photo_flag_thumbnails(rows)` after fetching rows

## Performance

Since photo flags lists are typically small (tens of items), the per-item `find_thumbnail()` call
(one `os.listdir` per SKU folder) adds negligible overhead (~1-2ms per item).
