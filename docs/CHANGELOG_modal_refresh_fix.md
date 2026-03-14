# CHANGELOG: Product Modal Refresh Fix

## Date: 2026-03-13

### Problem
When viewing a product modal and refreshing the page (F5), the Thai description, English description, brand, size, quantity, price, and most other product data disappeared. Only the SKU was preserved in the URL hash.

### Root Cause
On page refresh, `state.modalList` was empty. The navigation handler fell back to opening the modal with just `{ sku }`, missing all product fields.

### Fix
1. **New API endpoint** `/api/products/<sku>/detail` in `server.py` — returns full product data by SKU
2. **Updated `handleNavigation()`** in `app.js` — fetches product detail from API when product isn't in the local list
3. **New `fetchProductDetail()` function** in `app.js` — helper to call the detail endpoint

### Files Changed
- `server.py` (line ~812): New `get_product_detail()` endpoint
- `app.js` (line ~335): Updated hash navigation handler
- `app.js` (line ~1101): New `fetchProductDetail()` function
