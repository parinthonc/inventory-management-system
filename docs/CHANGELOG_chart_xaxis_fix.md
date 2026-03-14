# Changelog: Chart X-Axis Crowding Fix

**Date:** 2026-03-12  
**File Modified:** `app.js` (chart config in `fetchAndRenderArchivedHistory`)

## Problem
The ประวัติเคลื่อนไหว (Movement History) chart X-axis labels used the full Buddhist Era date format (`DD/MM/YYYY` e.g. `03/12/2561`), which at 10 characters wide caused labels to overlap and become unreadable — especially for products with many years of transaction history.

## Changes Made

### 1. Compact Date Labels (DD/MM/YY)
- Added a `shortBuddhistDate()` helper that converts `DD/MM/YYYY` → `DD/MM/YY` (e.g. `03/12/61`)
- Chart axis labels now use this shorter 8-character format
- **Full date is still shown in tooltips** via a separate `fullLabels[]` array

### 2. Better Auto-Skip & Spacing
- Reduced `maxTicksLimit` from `10` → `8` for cleaner spacing
- Enabled `autoSkip: true` with `autoSkipPadding: 12` to intelligently skip overlapping labels
- Set `maxRotation: 45` / `minRotation: 0` so Chart.js can rotate labels when needed

### 3. Smaller Font
- Set X-axis tick font size to `10px` (from default ~12px) for more compact labels

### 4. Enhanced Tooltips
- Background now uses a subtle purple border (`rgba(139, 92, 246, 0.3)`) matching the chart line color
- Added padding (10px) and rounded corners (6px radius)
- Custom `title` callback shows full date (`DD/MM/YYYY`) so no information is lost
- Custom `label` callback shows `ยอดคงเหลือ: X` in Thai for clarity

### 5. Layout Padding
- Added `layout.padding.bottom: 4` to prevent clipping of rotated labels

## Result
- Products with sparse history (few transactions): labels remain horizontal, clean and readable
- Products with dense history (12+ years like `03146-13201`): labels are properly auto-skipped and use compact format, fully readable without overlap
- Hovering any data point still shows the full date in tooltip
