# CHANGELOG: Remove Legacy `snapshots` & `import_log` Tables

**Date:** 2026-03-12  
**Scope:** `build_db.py`, `server.py`

## Summary

Removed the orphaned `snapshots` and `import_log` SQLite tables that were left over from the original ZIND-based data import workflow. These tables were never queried by the running webapp — the system now sources all data from CSV extraction scripts instead.

## What Changed

### `server.py`
- **Added `_drop_legacy_tables()`** migration at startup — drops `snapshots` and `import_log` tables from `inventory.db` if they still exist. This runs once and is a no-op afterwards.
- **Updated comment** on line ~1334 — removed stale reference to "keep snapshots intact".

### `build_db.py`
- **Removed `CREATE TABLE snapshots`** and **`CREATE TABLE import_log`** from `init_db()`.
- **Removed associated indexes** (`idx_snap_sku`, `idx_snap_date`).
- **Removed `import_snapshot()` function** — was responsible for importing ZIND files into the snapshots table.
- **Simplified `main()`** — removed the snapshot import loop; now only populates the `products` table from the latest ZIND file.

## Why

- The `snapshots` table stored historical qty/price per SKU from ZIND report files.
- The `import_log` table tracked which ZIND files had been imported.
- Neither table was ever queried by `server.py`, `app.js`, or `index.html`.
- All historical data is now served from `stock_ledger_full.csv` (via in-memory caches), and product data comes from `product_master_active.csv`.
- Removing these tables reduces the database size and eliminates dead code.

## Impact

- **Zero impact on webapp functionality** — no code path in the running server ever read from these tables.
- **Database size reduced** — the orphaned data is dropped from `inventory.db`.
- `build_db.py` is still functional for its remaining purpose (initial product table setup from ZIND files), though it is rarely run since `_reload_master_from_csv()` in `server.py` is the primary mechanism.
