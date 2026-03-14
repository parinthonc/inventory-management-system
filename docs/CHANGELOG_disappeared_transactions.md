# Changelog: Disappeared Transaction Detection

**Date:** 2026-03-14  
**Feature:** Detect, log, and alert when transactions disappear from the ERP

## Problem

When a transaction is **deleted** from the old ERP system (physically removed from binary files), the next ledger sync would silently overwrite the CSV with the new data. Users had no way to know that historical inventory records had been removed — a potential indicator of theft, error, or unauthorized adjustments.

## Solution: Detect → Log → Alert → Preserve

### Files Changed

| File | Changes |
|------|---------|
| `server.py` | Added ledger fingerprint snapshot before reload, diff after reload, `_handle_disappeared_transactions()` logger, `/api/disappeared-transactions` endpoint, and `disappeared_count`/`disappeared_transactions` in SSE changes payload |
| `index.html` | Added `#disappeared-warning` banner with expandable detail table |
| `index.css` | Added `.disappeared-warning` styles with red/amber glass theme and slide-in animation |
| `app.js` | Added `showDisappearedWarning()` function, dismiss/view toggle handlers, and checks last sync on page load |

### How It Works

1. **Before** a ledger sync reload, the server snapshots all ledger entry fingerprints (`part_code|sku_type|doc_ref|date`) from the in-memory cache.

2. **After** the reload, it builds a new set of fingerprints from the fresh data and computes the difference (old − new).

3. **If any entries disappeared:**
   - Writes a detailed batch entry to `ledger/disappeared_transactions.json` (persistent audit trail, keeps last 100 batches)
   - Logs to the server console with details of recent transactions
   - Broadcasts `disappeared_count` and `disappeared_transactions` (top 20) via SSE to all connected clients
   - Stores the count in `_last_sync_changes` so late-arriving clients see it too

4. **Frontend** shows a red warning banner at the top of the page with:
   - Count of disappeared transactions
   - "ดูรายละเอียด" button to expand a detail table showing date, doc_ref, part_code, category, qty_in, qty_out
   - Dismiss button to close the banner

### Edge Cases Handled

- **First sync** (no previous cache): Detection is skipped
- **Opening balances**: Filtered out (doc_ref = "OPENING" is synthetic)
- **Old vs recent**: Transactions are split — recent (last 365 days) are logged in detail, older ones are summarized by year
- **Large batches**: SSE payload capped at 20 entries; full log available via API
- **Log growth**: JSON file keeps only last 100 detection batches

### API

- `GET /api/disappeared-transactions` — Returns full audit log (array of batch objects)
- Each batch contains: `detected_at`, `total_count`, `recent_count`, `older_summary`, `transactions[]`
