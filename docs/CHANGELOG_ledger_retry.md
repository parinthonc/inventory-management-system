# CHANGELOG: Ledger Sync File Lock Retry

**Date:** 2026-03-13  
**Issue:** `[AutoSync] ledger sync failed: Script failed: PermissionError: [Errno 13] Permission denied`

## Root Cause

The `extract_stock_ledger_v4.py` script reads four binary files from `Z:\DATA.CTOTAL\` using 4 parallel threads:
- `CVINDTR1` (B-tree index + detail records)
- `CVINDTRN` (transaction headers)
- `CVINDMAS` (SKU master data)

The accounting software occasionally locks these files during normal operations.
When the auto-sync triggered the ledger extraction, the `CVINDTRN` file was locked,
causing a `PermissionError` that propagated through `concurrent.futures` and crashed the entire extraction.

The error traceback was also truncated at 500 chars in the server log format, which
hid the actual root cause (`PermissionError`) — only showing the generic `future.result()` traceback.

## Fix Applied

### 1. Retry logic in `extract_stock_ledger_v4.py`

Added `_read_file_with_retry()` helper that:
- Retries up to **5 times** on `PermissionError`
- Uses **exponential backoff**: 5s → 10s → 20s → 40s → 80s (max ~2.5 min total wait)
- Logs each retry attempt with the file name and delay
- Raises the original error if all retries exhausted

Applied to all four file reads:
- `parse_cvindtr1()` — CVINDTR1
- `parse_cvindtr1_detail()` — CVINDTR1
- `parse_cvindtrn()` — CVINDTRN (this was the failing one)
- `parse_cvindmas()` — CVINDMAS

### 2. Better error visibility in `server.py`

Increased the error message truncation limit from 500 → 1500 characters (line 233)
so future failures show the actual root cause instead of a cut-off traceback.

## Files Modified

- `python script/extract_stock_ledger_v4.py` — added `_read_file_with_retry()`, replaced 4x `open()` calls
- `server.py` — increased error stderr truncation from 500 → 1500 chars
