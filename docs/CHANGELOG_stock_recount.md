# CHANGELOG: Stock Recount Feature

**Date**: 2026-03-19  
**Scope**: `server.py`, `index.html`, `app.js`

## Summary

Replaced the manual stock discrepancy flagging system (where users selected a category: out_of_stock / less_than / more_than) with an automated **stock recount** flow. Users now input the real quantity they counted, and the system auto-determines the correct flag type. A dedicated history button shows the audit trail of all past recounts.

## Changes

### Backend (`server.py`)

- **Migration**: Added `recount_qty INTEGER DEFAULT NULL` column to `stock_flags` table
- **New table**: Created `recount_history` table to log every recount event for audit trail
- **`POST /api/products/<sku>/flag`**: Rewrote to support two modes:
  - **Recount mode** (new): Accepts `recount_qty`, auto-computes `flag_type`:
    - `recount_qty == 0 && system_qty > 0` → `out_of_stock`
    - `recount_qty < system_qty` → `less_than`
    - `recount_qty > system_qty` → `more_than`
    - `recount_qty == system_qty` → existing flag is **removed** (stock matches)
  - **Legacy mode**: Still accepts explicit `flag_type` for backward compatibility
  - Auto-generates descriptive note with counted/system/delta values
  - Every recount is logged to `recount_history` table
- **`GET /api/products/<sku>/recount-history`**: New endpoint returning recount history (newest first, max 20)
- **Product queries**: All product list, product detail, and flags listing queries now include `f.recount_qty`
- **`_flags_order()`**: Added `recount_qty` as a sortable column
- **JSON parsing**: Uses `request.get_json(force=True)` for reliability

### Frontend — Modal (`index.html` + `app.js`)

- **Report button**: "รายงานจำนวนของไม่ตรง" → "🔢 นับสต็อกจริง" with indigo color
- **Report dialog**: Replaced radio buttons with numeric input for "นับได้จริง"
- **Flag banner**: Shows recount delta info (e.g., "นับได้ 3 / ระบบ 10 (ต่างกัน -7)")
- **Detail grid**: Added "นับล่าสุด" (Last Recount) row showing counted qty and date
- **History button**: "📋 ประวัติ" button appears when recount history exists — toggles a closeable panel showing all past recounts (date, counted vs system, user)
- **`submitFlag()` → `submitRecount()`**: Sends `recount_qty` instead of `flag_type`

### Frontend — Flags Tab (`index.html` + `app.js`)

- Added **"Counted"** column header (sortable)
- Shows counted qty with color-coded badge
- Updated all `colspan` values from 8 → 9

## Migration Notes

- `recount_qty` column added via ALTER TABLE on startup
- `recount_history` table created via CREATE TABLE IF NOT EXISTS on startup
- Existing flags will have `recount_qty = NULL` — displayed as "-"
- Pickup view unchanged (uses legacy `flag_type` mode) — skipped per user request
