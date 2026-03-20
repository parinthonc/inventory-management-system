# CHANGELOG: Pickup Mode — Flag → Stock Recount

**Date**: 2026-03-20  
**Scope**: `app.js`, `index.css`

## Summary

Replaced the legacy flag button (🚩) in pickup mode with a **stock recount button** (🔢). Instead of selecting a category (out_of_stock / less_than / more_than), users now input the actual counted quantity. The system auto-determines the correct flag type by comparing the counted qty to the system qty — matching the recount flow already used in the product modal.

## Changes

### Frontend — Pickup Mode (`app.js`)

- **Button**: Changed `pickup-flag-btn` (🚩 "แจ้งปัญหาสต็อก") → `pickup-recount-btn` (🔢 "นับสต็อกจริง")
  - Now passes `data-qty` attribute with the system quantity
- **Popup**: Replaced `showPickupFlagPopup()` → `showPickupRecountPopup()`
  - Shows **system qty** prominently at the top
  - Provides a **numeric input** for "นับได้จริง" (actual count)
  - Submit button sends `recount_qty` to `POST /api/products/<sku>/flag` (recount mode)
  - Auto-determines flag type on the server side:
    - `recount_qty == 0 && system > 0` → `out_of_stock`
    - `recount_qty < system` → `less_than`
    - `recount_qty > system` → `more_than`
    - `recount_qty == system` → flag **removed** (stock matches)
  - Shows success/error status inline in the popup
  - Badge shows delta info (e.g., "⚠ น้อยกว่าระบบ (นับ 3, -7)")
  - Auto-checks item off and updates group/progress counters
  - Viewport-aware positioning (flips up if near bottom edge)
  - Input validation with shake animation
  - Enter key submits
- **Click handler**: Updated `handlePickupItemClick()` to detect `.pickup-recount-btn` instead of `.pickup-flag-btn`

### Frontend — Styles (`index.css`)

- Replaced `.pickup-flag-btn` and `.pickup-flag-popup` styles with:
  - `.pickup-recount-btn` — indigo-themed button (was red)
  - `.pickup-recount-popup` — fixed popup with input field styling
  - `.pickup-recount-input` — monospace, centered number input (no spinners)
  - `.pickup-recount-submit` — indigo gradient button
  - `.pickup-recount-status` — success/error status messages
  - Light theme overrides for all new elements
  - Input shake animation for validation errors

### Backend

- **No changes** — reuses existing `POST /api/products/<sku>/flag` endpoint (recount mode)

## Notes

- The existing flagged item visual styles (`.pickup-flagged`, `.pickup-flagged-badge`) remain unchanged
- The recount popup properly cleans up old flag classes before applying new ones
- Existing flags tab and product modal recount functionality are unaffected
