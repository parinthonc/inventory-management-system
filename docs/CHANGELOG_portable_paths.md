# CHANGELOG: Portable Paths (2026-03-13)

## Problem
All file paths were hardcoded to `D:\CW\inventory management system\`, making it
impossible to run the project from a different folder or drive without manually
editing multiple files.

## Solution
Replaced all hardcoded absolute paths with dynamic paths derived from each
script's `__file__` location. The project is now **fully portable** — copy the
folder anywhere and it just works.

## Files Changed

### `server.py` (2 changes)
- **Line 21**: `sys.path.insert(0, r'D:\CW\...')` → uses `os.path.dirname(os.path.abspath(__file__))`
- **Line 27**: `DB_FILE = r'D:\CW\...\inventory.db'` → uses `os.path.join(...)` relative to `__file__`

### `config.ini` (3 changes)
- `archived_ledger_dir` → `ledger` (relative)
- `db_file` → `inventory.db` (relative)
- `logo_file` → `logo\logo.png` (relative)

### `build_db.py` (1 change)
- Added `_resolve_path()` helper that converts relative config paths to absolute
  paths using `BASE_DIR`. Absolute paths in config.ini still work unchanged.

### `python script\extract_stock_ledger_v4.py` (1 change)
- `OUTPUT_DIR = r"D:\CW\...\ledger"` → derived from script's parent directory

### `python script\extract_invoice.py` (1 change)
- `OUTPUT_DIR = r"D:\CW\...\invoice"` → derived from script's parent directory

### `python script\extract_product_master.py` (1 change)
- `OUT_DIR = r"D:\CW\...\product master table"` → derived from script's parent directory

### `python script\extract_customer_master.py` (1 change)
- `OUT_DIR = r"D:\CW\...\customer master table"` → derived from script's parent directory

## What Still Uses Absolute Paths (By Design)
- `Z:\DATA.CTOTAL\...` and `Z:\DATA.CW\...` in extraction scripts — these are the
  ERP server source files and must point to wherever the network share is mapped.
- `config.ini` image directories (`primary_dir`, `secondary_dir`) — these point to
  external image folders that are NOT inside the project, so they must remain
  configurable absolute paths.

## How It Works
All scripts now use this pattern:
```python
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_SCRIPT_DIR)  # for scripts in subfolders
```
This resolves to the correct absolute path regardless of where the project is installed.
