# Changelog: Type Column in Photo Flags Tab

**Date:** 2026-03-19

## Summary
Added the product **type** (suffix) to the "📷 รายการที่ต้องถ่ายรูปเพิ่ม" tab in **both views**:
- **Table view**: Full sortable "Type" column after Part Code
- **Pickup view**: Compact purple type badge next to the part code

## Files Changed

### `index.html`
- Added sortable `Type` column header (`data-sort="suffix"`) to the photo flags table

### `app.js`
- `renderPhotoFlags()`: Added Type `<td>` with `brand-badge` styling after Part Code
- `renderPickupMode()`: Added `.pickup-type-badge` inline next to part code
- Updated `colspan` from 11 → 12 for loading/empty/error states

### `server.py`
- Added `'suffix': 'p.suffix'` to `_photo_flags_order()` sort map
- Added `p.suffix` to the pickup API SQL SELECT clause
- Included `suffix` in the pickup item dictionary

### `index.css`
- Added `.pickup-type-badge` styles (purple theme, compact inline badge)
- Added light theme variant for the badge
