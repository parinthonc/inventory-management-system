# Changelog: Sort Products by Last Photo Date

**Date:** 2026-03-19

## Summary
The **Image** column header in the Products tab is now clickable and sorts products by the creation date of their most recent photo. This uses filesystem file modification times directly (not JSON metadata).

## Changes

### server.py
- Added `last_photo_date` TEXT column to the `products` table (auto-migrated via `ALTER TABLE`)
- New `_get_last_photo_date_for_dir(custom_dir)` — returns the most recent image file's `mtime` as ISO timestamp
- New `_update_last_photo_dates()` — scans all product image directories at startup and populates the column
- Added `'last_photo_date'` to the `valid_sorts` whitelist in `/api/products`
- `ORDER BY` uses `CASE WHEN ... THEN 1 ELSE 0 END` to push products with no photos to the end
- Image upload handler (`upload_product_image`) now also updates `last_photo_date`
- Image delete handler (`delete_custom_image`) now also updates `last_photo_date`

### index.html
- Changed `<th class="col-img">Image</th>` to `<th class="col-img sortable" data-sort="last_photo_date">Image <span class="sort-arrow"></span></th>`

### No changes needed in app.js
The existing `setupSortableHeaders()` utility automatically handles the new sortable header.

## How It Works
1. At server startup, `_update_last_photo_dates()` scans `IMAGE_DIR_CUSTOM` subdirectories
2. For each folder, it finds the newest image file by `os.path.getmtime()` and stores the timestamp in the DB
3. When images are uploaded or deleted, the column is updated immediately for that product
4. Clicking the Image column header triggers the standard three-state sort cycle: ascending → descending → natural
