# Compact Product Modal for Smaller Screens

**Date:** 2026-03-13  
**Issue:** On employee screens (physically smaller displays), the product modal's top half was too large, occupying more than half the screen. This left only 1-2 entries visible in the รายการเคลื่อนไหว (movement history) table at the bottom.

## Changes Made

### CSS (`index.css`)

| Element | Property | Before | After | Purpose |
|---------|----------|--------|-------|---------|
| `.modal-top-row` | `max-height` | `50vh` | `38vh` | Reduce top section height |
| `.modal-gallery` | `flex/max-width` | `30%` | `25%` | Narrower image panel |
| `.modal-gallery` | `padding` | `1rem` | `0.5rem` | Less padding around gallery |
| `.main-image-container` | `margin-bottom` | `0.5rem` | `0.35rem` | Tighter spacing |
| `.thumbnail-strip` | `max-height` | `80px` | `55px` | Smaller thumbnail area |
| `.thumbnail-strip` | `gap` | `0.35rem` | `0.25rem` | Tighter thumbnail gaps |
| `.gallery-thumb` | `width/height` | `48px` | `40px` | Smaller thumbnails |
| `.modal-details` | `padding` | `1rem 1.5rem` | `0.5rem 1rem` | Less padding in details |
| `.modal-bottom-left` | `padding` | `0.75rem 1rem` | `0.5rem 0.75rem` | Tighter chart area |
| `.modal-bottom-right` | `padding` | `0.75rem 1rem` | `0.5rem 0.75rem` | Tighter table area |
| `.sku-badge` | `font-size` | `1.2rem` | `0.85rem` | Smaller type badge |
| `.sku-badge` | `padding` | `0.35rem 1rem` | `0.2rem 0.6rem` | Compact badge |
| `.part-code` | `font-size` | `1.5rem` | `1.15rem` | Smaller part code |
| `.name-eng` | `font-size` | `1rem` | `0.85rem` | Smaller description |
| `.name-thai` | `margin-bottom` | `1rem` | `0.5rem` | Less trailing space |
| `.detail-grid` | `gap` | `0.75rem` | `0.4rem` | Tighter grid |
| `.detail-item` | `gap` | `0.25rem` | `0.1rem` | Compact items |
| `.detail-item .label` | `font-size` | `0.875rem` | `0.7rem` | Smaller labels |
| `.detail-item .value` | `font-size` | `1.125rem` | `0.95rem` | Smaller values |
| `.qty-value` | `font-size` | `1.5rem` | `1.1rem` | Smaller qty display |
| `.price-value` | `font-size` | `1.5rem` | `1.1rem` | Smaller price display |
| `.history-table` | `font-size` | `1.3125rem` | `1rem` | Compact table rows |
| `.history-table th,td` | `padding` | `0.5rem 0.75rem` | `0.3rem 0.5rem` | Tighter table cells |
| `.history-table th` | `font-size` | `1.125rem` | `0.875rem` | Smaller headers |
| `.sales-by-year-section` | `padding` | `0.75rem 1.5rem 0.5rem` | `0.35rem 1rem 0.25rem` | Compact year section |
| `.sales-by-year-grid` | `gap` | `0.5rem` | `0.3rem` | Tighter year cards |
| `.year-card` | `padding` | `0.5rem 0.85rem` | `0.25rem 0.6rem` | Smaller year cards |
| `.year-card` | `min-width` | `80px` | `65px` | Narrower year cards |
| `.year-card .year-label` | `font-size` | `0.75rem` | `0.65rem` | Smaller year labels |
| `.year-card .year-qty` | `font-size` | `1.1rem` | `0.9rem` | Smaller year qty |

### Responsive Media Query (`@media max-width: 1280px`)
- Gallery width reduced from `25%` → `20%`
- Added `modal-top-row` max-height: `35vh`

### HTML (`index.html`)
- Report button font-size reduced from `1.5rem` → `0.9rem`
- Report section `margin-top` / `padding-top` reduced from `1rem` → `0.5rem`
- Titles section `margin-top` reduced from `1rem` → `0.5rem`

## Result
The top half of the product modal now takes up significantly less vertical space (~38% of viewport instead of ~50%), and all text/UI elements inside are more compact. This allows the bottom row (ประวัติเคลื่อนไหว chart + รายการเคลื่อนไหว table) to show many more entries without scrolling.

---

## Update 2: Relocated จำนวนจ่ายออกรายปี (Annual Output) Section

**Issue:** The Annual Output year cards occupied a full-width horizontal band between the top row and bottom row, consuming additional vertical space that could go to the movement history table.

**Solution:** Moved the section **inside** the `modal-details` panel (right column of the top row), positioned below the report button. It now scrolls with the product details rather than occupying its own dedicated row.

### Changes
- **`index.html`**: Moved `#modal-sales-by-year` div from standalone position (between top/bottom rows) into `.modal-details` div, after the report section
- **`index.css`**: Removed `border-bottom` from `.sales-by-year-section` (no longer needed as a separator)
- Inline styles adjusted: reduced header font to `0.7rem`, compact padding, no bottom border

### Layout Before
```
┌─────────────────────────────────────────┐
│  Top Row: Gallery | Details + Report    │  38vh
├─────────────────────────────────────────┤
│  จำนวนจ่ายออกรายปี (year cards)          │  ~40px band
├─────────────────────────────────────────┤
│  Chart (left)  |  รายการเคลื่อนไหว (right) │  remaining
└─────────────────────────────────────────┘
```

### Layout After
```
┌─────────────────────────────────────────┐
│  Top Row: Gallery | Details + Report    │  38vh
│                   | + Annual Output     │  (scrollable)
├─────────────────────────────────────────┤
│  Chart (left)  |  รายการเคลื่อนไหว (right) │  MORE space!
└─────────────────────────────────────────┘
```
