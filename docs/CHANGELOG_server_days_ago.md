# Changelog: Server-Side "x วันก่อน" Calculation

**Date:** 2026-03-13  
**Issue:** Some user PCs have incorrect system dates, causing the "x วันก่อน" (x days ago) display to be inaccurate.

## Problem

The "x วันก่อน" relative date shown next to `last_sold_date` in the product list was calculated **client-side** using `new Date()` from the user's PC. If the PC clock was wrong (e.g., set to a different year), the displayed "x days ago" would be incorrect.

## Solution

Moved the calculation to the **server side** so all clients get the same, accurate result based on the server's clock.

### Changes

#### `server.py` — `/api/products` endpoint
- Added `days_ago` field to each product in the response:
  - `days_ago > 0` → the sale was N days in the past
  - `days_ago == 0` → sold today ("วันนี้")
  - `days_ago < 0` → future date (data anomaly)
  - `days_ago == null` → no `last_sold_date` available
- Added `server_today` field to the API response (ISO format `YYYY-MM-DD`) for reference

#### `app.js` — `renderProducts()` function
- Removed `new Date()` client-side calculation
- Now uses the server-provided `p.days_ago` value directly
- Fallback: if `days_ago` is null/undefined but `last_sold_date` exists, shows the date without a relative label

## Impact

- **No visual change** for users with correct PC clocks
- **Fixes incorrect display** for users with wrong PC dates
- All relative date calculations now come from the server's system clock
