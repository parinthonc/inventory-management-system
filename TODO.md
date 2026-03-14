# Project Notes

## Data Sources
- **On-hand quantity** is sourced from `stock_ledger_full.csv` (last `running_balance` per part). Falls back to ZIND-based qty if no CSV data exists.
- The CSV is loaded into memory at startup and cached. If the CSV file changes, the server must be restarted to pick up the new data.

## UI Adjustments (Hidden Sections)
- **"Stock History"** — hidden in product modal. Unhide by removing `hidden` class from `history-section` div in `index.html`.
- **"Possible Titles"** — hidden in product modal. Unhide by removing `hidden` class from `titles-section` div in `index.html`.
- **"Archived History (Old System)"** — visible, uses **Buddhist Era years** (+543) in dates.
