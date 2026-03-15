# CHANGELOG: Fix Flag Banner Overlap with Nav Controls

**Date:** 2026-03-15  
**Issue:** The modal navigation indicator ("1 / 2" pill at top-left) was overlapping and blocking the flag warning banner text inside the product detail modal.

## Problem

When viewing a flagged product in the product modal, the `modal-nav-controls` (position: absolute, top-left) would sit on top of the `modal-flag-banner`, blocking the flag icon (🚩) and the beginning of the warning text (e.g. "⚠️ สินค้าจริงน้อยกว่าระบบ").

## Fix

**File:** `index.css`  
**Change:** Added left padding to `.modal-flag-banner` so its content starts after the nav controls area.

```diff
 .modal-flag-banner {
-    padding: 0.75rem 1rem;
+    padding: 0.75rem 1rem 0.75rem 9.5rem;
 }
```

The `9.5rem` left padding ensures the flag icon and text are pushed past the absolutely-positioned navigation pill (~140px wide), making the full warning message visible.

## Verification

- Opened flagged product modal from the Flags tab
- Confirmed nav indicator ("1 / 2") and flag banner are no longer overlapping
- Both elements are fully visible and readable
