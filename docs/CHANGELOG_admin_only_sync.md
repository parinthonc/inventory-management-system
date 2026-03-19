# Admin-Only Refresh & Auto-Sync Buttons

**Date:** 2026-03-19

**Purpose:** Restrict Refresh and Auto-Sync controls so only admin users can click them. Non-admin users (viewers/guests) can still **see** the buttons but cannot interact with them.

## What Changed

### `app.js` — `_showUserUI()`
- After auth, checks `_currentUser.role === 'admin'`
- **Refresh buttons** (`refresh-invoice-btn`, `refresh-customer-btn`, `refresh-master-btn`, `refresh-ledger-btn`): set `disabled` and add `.admin-only-disabled` class for non-admins
- **Auto-sync toggles** (`sync-toggle-master`, `sync-toggle-ledger`, `sync-toggle-customer`, `sync-toggle-invoice`): set `disabled` on checkbox and add `.admin-only-disabled` to the parent label for non-admins
- **Click-to-sync dots & labels** (`.sync-item-dot`, `.sync-item-label`): set `pointer-events: none` for non-admins so manual sync via click is blocked

### `index.css`
- Added `.admin-only-disabled` class: `opacity: 0.4`, `pointer-events: none`, `cursor: not-allowed`
- `button.admin-only-disabled` keeps `pointer-events: auto` so tooltip ("Admin only") still appears on hover

## Behavior
| User Role   | Buttons Visible | Buttons Clickable |
|-------------|----------------|-------------------|
| Admin       | ✅             | ✅                |
| Viewer      | ✅             | ❌ (greyed out)   |
| Guest       | ✅             | ❌ (greyed out)   |

When a non-admin user logs in as admin, the page reloads and buttons become fully functional.
