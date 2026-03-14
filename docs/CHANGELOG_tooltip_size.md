# Changelog: Chart Tooltip Size Increase

**Date:** 2026-03-13  
**File Modified:** `app.js`

## What Changed

Scaled the Chart.js **tooltip** (the bubble that follows your cursor when hovering on the history chart) to **1.5x** its original size.

### Before → After

| Property      | Before | After |
|---------------|--------|-------|
| `padding`     | 10     | 15    |
| `cornerRadius`| 6     | 8     |
| `titleFont.size` | 12  | 18    |
| `bodyFont.size`  | 12  | 18    |

## Why

To improve readability of the tooltip on the ประวัติเคลื่อนไหว (movement history) chart.

## Location in Code

`app.js` → `fetchAndRenderArchivedHistory()` → Chart.js `options.plugins.tooltip` (around line 2155)
