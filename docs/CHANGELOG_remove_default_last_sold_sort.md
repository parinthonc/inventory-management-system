# CHANGELOG: Remove Default Sort by วันที่ขายล่าสุด

**Date:** 2026-03-16

## Summary
Removed the default sort filter that was set to "วันที่ขายล่าสุด" (Last Sale Date, descending). The default sort is now **Part Code (ascending)**, which was the original default before the change.

## Changes Made

### `index.html`
- Moved `selected` attribute from `last_sold_date` option to `part_code` option in the sort dropdown
- Swapped the initial visibility of sort direction icons: ascending arrow (↑) is now visible by default, descending arrow (↓) is hidden

### `app.js`
- Changed `state.sort` initial value from `'last_sold_date'` to `'part_code'`
- Changed `state.sortDir` initial value from `'desc'` to `'asc'`
- Updated `setupSortableHeaders` call for the products table from `('last_sold_date', 'desc')` to `('part_code', 'asc')`

## Reason
User requested removal of the default filter set to วันที่ขายล่าสุด.
