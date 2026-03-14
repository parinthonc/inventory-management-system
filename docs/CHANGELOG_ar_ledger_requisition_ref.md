# AR Ledger: Added requisition_ref Column

**Date:** 2026-03-09  
**Issue:** `requisition_ref` field from `ar_ledger.csv` and `ar_ledger_cv.csv` was not displayed on the website.

## Root Cause

The CSV files contain a `requisition_ref` column (ใบเบิก) and the server's `_load_csv()` function already loaded all columns into memory. However, the frontend was not rendering this column:

1. **`index.html`** — The AR ledger `<thead>` had 9 columns but no `requisition_ref` header
2. **`app.js`** — The `renderArLedger()` function only rendered 9 `<td>` cells
3. **`server.py`** — The search fields for `/api/ar-ledger` did not include `requisition_ref`

## Changes Made

### `index.html`
- Added `<th>ใบเบิก</th>` column header to the AR ledger table
- Updated `colspan` from `9` to `10` for the loading spinner row

### `app.js`
- Added `<td>` for `requisition_ref` in `renderArLedger()` (monospace font, 0.9rem)
- Updated all `colspan` values in `fetchArLedger()` and `renderArLedger()` from `9` to `10`

### `server.py`
- Added `'requisition_ref'` to the search fields array in `get_ar_ledger()` so users can search by requisition reference number

## Notes

- The server needs to be restarted for the `server.py` change to take effect
- The `requisition_ref` values are particularly present in CV (off-book) data (e.g., `00357000048`)
- CW data mostly has empty `requisition_ref` values (displayed as `-`)
