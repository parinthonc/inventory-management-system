# CHANGELOG — Bug Fixes (2026-03-12)

Fixes for functional bugs and code quality issues found during webapp analysis.

---

## server.py

### Thread-Safe Cache Loading (Functional Bug)
**Problem:** Global caches (`archived_history_cache`, `archived_qty_cache`, etc.) were cleared to empty dicts/lists at the start of `load_archived_history_cache()`, then gradually rebuilt. Any API request during this window would receive empty or partial data.

**Fix:** Introduced `_cache_lock` (RLock). Cache data is now built into local variables (`new_history`, `new_qty`, etc.) and atomically swapped into the globals at the end under the lock.

### Shadowed `datetime` Import (Functional Bug)
**Problem:** Line 548 had `from datetime import datetime, timedelta` inside `get_products()`, shadowing the module-level `import datetime`. Future code using `datetime.datetime` would crash.

**Fix:** Replaced with `datetime.datetime.now()` and `datetime.timedelta()` using the already-imported module.

### Unnecessary Ledger Reload on Master Sync (Code Quality / Performance)
**Problem:** `_reload_master_from_csv()` set `archived_history_cache = None` and called `load_archived_history_cache()`, triggering a full re-read of the entire ledger CSV. Only the product table had changed — the ledger data was untouched.

**Fix:** Replaced with `_sync_csv_data_to_db()` + `_build_moves_list()`, which only re-syncs the cached qty/date values to the updated product rows and rebuilds the in-memory moves list.

### Duplicate `INVOICE_DIR` Definition (Code Quality)
**Problem:** `INVOICE_DIR` was defined identically at line 28 and again at line 986.

**Fix:** Removed the duplicate at line 986 and added a comment pointing to the canonical definition.

---

## app.js

### `from_to` Attribute XSS Risk (Code Quality)
**Problem:** In the archived history table, `h.from_to` was inserted directly into `data-customer-code="${h.from_to}"` and display text without escaping. Special characters in customer codes could break the HTML or enable attribute injection.

**Fix:** Wrapped both the attribute value and display text with `escapeHtml()`.

### SSE Reconnect Doesn't Re-Sync Toggle State (Code Quality)
**Problem:** On SSE reconnection (after server restart), the client didn't re-push its saved toggle states. The server would have all toggles set to `false` (default), creating a mismatch.

**Fix:** Added `syncConfigToServer(loadToggleStates())` in the `evtSource.onopen` handler so local state is re-pushed on every reconnect.

---

## index.html + index.css

### Import CSV Modal Full-Screen (Code Quality)
**Problem:** The Import CSV modal div used `class="modal card glass-dark"`. The `.modal` CSS class sets `width: 100%; height: 100%; border-radius: 0;`, designed for the product detail modal. This overrode the inline `max-width: 560px; width: 90%` style, making the Import CSV popup appear full-screen.

**Fix:** Renamed the class to `import-csv-dialog` and added a new CSS rule with `position: relative; border-radius: var(--radius-lg)` — no longer inherits the full-screen sizing.

---

## index.html

### Increase Font Size of "รายงานของไม่ตรงหน้าเครื่อง" Button (UI Improvement)
**Change:** Added `font-size: 1.05rem` to the inline style of `#btn-report-issue`.

**File:** `index.html` line ~731
