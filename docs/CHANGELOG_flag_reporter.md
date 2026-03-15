# Changelog: Flag Reporter Tracking & Admin-Only Resolve

**Date:** 2026-03-15

## Summary
Two enhancements to the stock flags system:
1. **Reporter tracking** — Each flag now records which user reported it (`flagged_by` column).
2. **Admin-only resolve** — Only admin users can resolve (delete) flags. Viewers see the flags but cannot dismiss them.

## Backend Changes (`server.py`)

### Database
- Added `flagged_by TEXT DEFAULT ''` column to `stock_flags` table
- Includes a safe migration (`ALTER TABLE ... ADD COLUMN`) for existing databases

### API Endpoints
- **POST `/api/products/<sku>/flag`** — Now stores `session['user']` in `flagged_by`
- **DELETE `/api/products/<sku>/flag`** — Protected with `@admin_required` (returns 403 for non-admin)
- **GET `/api/flags`** — Now includes `flagged_by` in response
- All product queries that JOIN `stock_flags` now include `flagged_by`

### Logging
- Flag creation and resolution are now logged to console with username

## Frontend Changes (`app.js`)

### Flags Tab
- **Reporter name** displayed under the date column as "รายงานโดย: **username**"
- **Resolve button** only rendered for admin users (`_currentUser.role === 'admin'`)

### Error Handling
- Resolve click handler guards against non-admin users
- 403 responses show Thai message: "เฉพาะ Admin เท่านั้นที่สามารถ Resolve ได้"
