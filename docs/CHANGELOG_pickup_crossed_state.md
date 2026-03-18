# Changelog: Three-State Pickup Checkbox

**Date:** 2026-03-18  
**Type:** Feature Enhancement

## Summary
Added a third "crossed" state (red ✗) to the pickup mode checkbox toggle. The cycle is now:
**Unchecked** (empty box) → **Checked** (green ✓) → **Crossed** (red ✗) → **Unchecked** (repeat)

## Changes

### `server.py`
- Added `status` column to `pickup_checks` table (values: `'checked'` or `'crossed'`)
- Auto-migration adds the column to existing databases
- POST `/api/pickup-checks/<sku>` now accepts `{ "status": "checked" | "crossed" }` in body
- Pickup data endpoint returns `status` field per item

### `app.js`
- `handlePickupItemClick` now implements 3-state toggle cycle
- `renderPickupMode` renders the `crossed` state from server data
- Progress counter and group headers count both `.checked` and `.crossed` items
- Reset clears both checked and crossed states

### `index.css`
- Added `.pickup-item.crossed .pickup-checkbox` — red background/border (`#ef4444`)
- Added `.pickup-item.crossed .pickup-checkbox::after` — white "✕" cross mark
- Added `.pickup-item.crossed .pickup-item-info` — strikethrough with red decoration color
