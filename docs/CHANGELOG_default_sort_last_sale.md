# Changelog: Default Sort Changed to Last Sale Date

**Date:** 2026-03-13  
**Change Type:** UX Improvement

## Summary
Changed the default product sort order from **Part Code (ascending)** to **วันที่ขายล่าสุด / Last Sale Date (descending)**, so the most recently sold items appear first when the page loads.

## Files Modified

### 1. `app.js`
- **Line 12-13**: Changed initial state `sort` from `'part_code'` to `'last_sold_date'` and `sortDir` from `'asc'` to `'desc'`
- **Line 371**: Updated `setupSortableHeaders` default parameters from `'part_code', 'asc'` to `'last_sold_date', 'desc'`

### 2. `server.py`
- **Line 655-656**: Changed server-side default `sort` from `'part_code'` to `'last_sold_date'` and `dir` from `'asc'` to `'desc'`
- **Line 662**: Changed invalid sort fallback from `'part_code'` to `'last_sold_date'`
- **Line 742-744**: Changed `relevance` sort fallback (when no search term) from `'part_code'` to `'last_sold_date'`

### 3. `index.html`
- **Line 132**: Removed `selected` attribute from `part_code` option in sort dropdown
- **Line 140**: Added `selected` attribute to `last_sold_date` option in sort dropdown
- **Lines 167-173**: Swapped sort direction icon visibility — desc icon shown by default, asc icon hidden (matching the new default descending direction)

## Behavior
- Products are now sorted by **last sale date in descending order** by default
- Most recently sold items appear first
- Users can still change the sort to any other field via the dropdown or by clicking column headers
- The sort direction button icon correctly shows the downward arrow (descending) on initial load
