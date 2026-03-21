# Changelog: Bug Audit Fixes (2026-03-20)

Comprehensive bug fixes based on a full codebase audit of `server.py`, `app.js`, and `index.html`.

## Security Fixes

### `@admin_required` added to 8 unprotected endpoints
**Files:** `server.py`

The following endpoints previously had **no authentication or role checks**, allowing any user (including unauthenticated users) to trigger expensive operations or modify system settings:

| Endpoint | Impact |
|---|---|
| `POST /api/sync/config` | Modify auto-sync toggle states |
| `POST /api/sync/trigger/<source>` | Trigger background extraction scripts |
| `POST /api/refresh-ledger` | Run stock ledger extraction from Z: drive |
| `POST /api/refresh-master` | Run product master extraction |
| `POST /api/refresh-customer-master` | Run customer master extraction |
| `POST /api/refresh-invoices` | Run invoice extraction |
| `POST /api/products/<sku>/images/hide` | Hide product images |
| `POST /api/products/<sku>/images/unhide` | Restore hidden images |

All now require admin role via the `@admin_required` decorator. The frontend already disabled these buttons for non-admins, but the API was unprotected.

### XSS prevention: `escapeHtml()` now escapes single quotes
**Files:** `app.js` (line 2758)

The `escapeHtml()` function did not escape single quotes (`'`), creating an XSS vector when embedded in `onclick` HTML attributes (e.g., admin user list delete/reset buttons, backup restore/delete buttons). Now escapes `'` → `&#39;`.

### `escapeHtml` added to disappeared transaction table
**Files:** `app.js` (line ~5246)

Fields `date`, `doc_ref`, `part_code`, and `category_name` from server sync change data were inserted into HTML without escaping, risking XSS if data contained HTML characters.

## Data Integrity Fixes

### `last_photo_date` preserved during master refresh
**Files:** `server.py` (lines 1400, 3207)

When the product master is refreshed, all rows in the `products` table are deleted and re-inserted. The `last_photo_date` column was **permanently lost** because it's derived from filesystem metadata, not the CSV data. Now both `_reload_master_from_csv()` and `/api/refresh-master` call `_update_last_photo_dates()` after rebuild to restore these values.

## DoS Prevention

### `per_page` capped at 500
**Files:** `server.py` (lines 1792, 2818, 2984)

The products, customers, and invoices API endpoints accepted any `per_page` value. A request with `per_page=999999` would return the entire dataset in one query, potentially causing memory exhaustion. Now capped at 500.

## Functional Fixes

### Recount history colors fixed (dark theme)
**Files:** `app.js` (lines 3241-3248)

All recount history color branches were set to `#000000` (black), making text **invisible in dark theme**. Fixed:
- `more_than` / `match` → green (`#34d399`)
- `less_than` / `out_of_stock` → red (`#f87171`)
- default → `var(--text-primary)`

### Pickup auto-check sends proper JSON body
**Files:** `app.js` (line 4075)

When a pickup recount auto-checks an item, it was sending a bare `POST` without headers or body. Now sends `{ status: 'checked' }` with `Content-Type: application/json`.

### Photo flags empty state colspan fixed
**Files:** `app.js` (line 3569)

The empty state `<td colspan="11">` didn't span all 12 columns of the photo flags table. Fixed to `colspan="12"`.

### Event listener leak in pickup recount popup
**Files:** `app.js` (lines 4111, 4134)

When the recount popup auto-closed after a successful submit, the document-level `closePopup` click listener was never removed. This leaked a listener on every successful recount. Now properly cleaned up in both dismiss paths.

### SSE reconnect label preserves toggle count
**Files:** `app.js` (line 5017)

On SSE reconnection, the sync label was overwritten to "Auto-Sync: Reconnecting..." losing the "(2/4)" toggle count suffix. Now preserves the existing label text and appends the reconnecting status.
