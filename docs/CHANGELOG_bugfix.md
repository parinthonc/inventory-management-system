# CHANGELOG — Bug Fixes (2026-03-15)

## server.py

### Thread Safety — Cache Lock Snapshots
- `get_products`: Snapshot `archived_qty_cache` and `archived_history_cache` under `_cache_lock` before reading
- `get_product_detail`: Snapshot `archived_qty_cache` under `_cache_lock` before reading
- `get_archived_history`: Snapshot `archived_history_cache` under `_cache_lock` before reading
- `_sync_csv_data_to_db`: Snapshot both qty and sale caches under lock before DB writes
- `_build_moves_list`: Snapshot `archived_history_cache` under lock; build into local var then atomic swap

### DB Connection Leak Protection
- `get_product_detail`: Wrapped DB access in `try/finally` to ensure `conn.close()` on errors
- `flag_product`: Wrapped DB access in `try/finally` to ensure `conn.close()` on errors

### per_page Edge Case
- All 5 paginated endpoints (`get_products`, `get_all_moves`, `get_flags`, `get_customers`, `get_invoices`): Added `per_page = max(1, ...)` to prevent ZeroDivisionError

---

## app.js

### XSS Prevention
- `renderCustomers`: Escape `customer_code`, `customer_name`, `phone` via `escapeHtml()`
- `renderInvoices`: Escape `invoice_number`, `customer_code`, `customer_name`
- `renderFlags`: Escape `part_code`, `name_eng`, `name_thai`, `brand`
- `_loadAdminUsers`: Escape `username`, `role`, `created_at` in admin panel table

### Event Listener Duplication
- `_showUserUI`: Added `_userUIBound` guard flag to prevent re-binding admin and logout listeners on re-login
- `init()`: Added `_initialized` guard flag to prevent duplicate setup on session re-check
