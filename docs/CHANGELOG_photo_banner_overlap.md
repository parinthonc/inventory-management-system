# Photo Flag Banner Overlap Fix

**Date:** 2026-03-19  
**Issue:** The "📷 ต้องการรูปเพิ่ม" photo flag banner text in the product modal was being blocked/hidden by the product list navigation indicator (e.g., "2/5").

## Root Cause
The `.modal-nav-controls` pill (containing prev/next buttons and "2/5" indicator) is absolutely positioned at `top: 1rem; left: 1rem` inside the modal. The `.modal-photo-flag-banner` had uniform padding (`0.75rem 1rem`), causing its left-side content to overlap with the nav indicator.

## Fix
Added `padding-left: 9.5rem` to `.modal-photo-flag-banner` in `index.css`, matching the same approach used by `.modal-flag-banner` (stock flag banner). This pushes the banner text to the right, clearing the navigation indicator area.

### Changed File
- **`index.css`** (line ~3349): Changed `padding: 0.75rem 1rem` → `padding: 0.75rem 1rem 0.75rem 9.5rem`
