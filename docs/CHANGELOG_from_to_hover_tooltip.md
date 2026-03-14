# CHANGELOG: จาก/ให้ Column Hover Tooltip (Customer Name)

**Date:** 2026-03-14

## Summary
Added a hover tooltip on the **จาก/ให้** (From/To) column in the product modal's archived history table. When hovering over a customer code, a big floating bubble displays the customer's full name.

## Changes

### 1. `server.py` — Enrich archived history API with customer name
- **`get_archived_history()`** (line ~1491): The `/api/products/<sku>/archived-history` endpoint now includes a `from_to_name` field for each history entry by looking up the customer code in the already-loaded `customer_master_cache`.
- **Zero performance cost** — no extra file reads or DB queries; all data is already in memory.

### 2. `app.js` — Add hover bubble HTML to the จาก/ให้ cell
- **`fetchAndRenderArchivedHistory()`** (line ~2179): The `from_to` cell is now wrapped in a `<span class="from-to-hover-wrap">` container. When `from_to_name` is present, a `<span class="from-to-bubble">` element is added displaying the customer name.
- The existing click-to-navigate behavior on the customer code link is preserved.

### 3. `index.css` — Hover bubble styling
- Added `.from-to-hover-wrap` (positioning context) and `.from-to-bubble` (the tooltip) styles.
- The bubble has a large font (1.15rem, bold), glassy dark background, blue accent border, downward-pointing arrow, and a smooth fade-in animation.
- **Purely CSS-driven** — no JavaScript event listeners, no timers, no network requests on hover. Zero resource drain.

## Technical Notes
- The tooltip uses `display: none / block` toggled by `:hover`, which is the most lightweight tooltip approach possible.
- `pointer-events: none` on the bubble prevents it from interfering with mouse interactions.
- `z-index: 9999` ensures the bubble appears above all other elements in the modal.
