# CHANGELOG: Sort By Dropdown Update (Products Tab)

**Date:** 2026-03-12  
**File:** `index.html`

---

## Changes

### 1. Label renamed to Thai
- **Before:** `Sort By`
- **After:** `เรียงตาม`

### 2. Dropdown options expanded to include every sortable product column

| Value | Display Name | Status |
|-------|-------------|--------|
| `part_code` | Part Code | ✅ Already existed |
| `suffix` | Type | 🆕 Added |
| `brand` | Brand | 🆕 Added |
| `name_eng` | Description | ✅ Renamed from "Name" → "Description" to match `<th>` |
| `size` | Size/Spec (ขนาด) | 🆕 Added |
| `locations` | Location (คลัง) | 🆕 Added |
| `qty` | Qty | ✅ Renamed from "Quantity" → "Qty" to match `<th>` |
| `sale_price` | ราคาต่อหน่วย | ✅ Renamed from "Price" → "ราคาต่อหน่วย" to match `<th>` |
| `last_sold_date` | วันที่ขายล่าสุด | 🆕 Added |
| `amount_sold` | Amount Sold | 🆕 Added |
| `relevance` | Relevance | ✅ Moved to bottom (only relevant during text search) |

### Notes for AI/Human
- The `value` attributes in the `<option>` elements correspond to the `data-sort` attributes on the `<th>` headers in the product table
- Display names now match the column header text exactly for consistency
- The `relevance` option is moved to the bottom since it only applies when a search query is active
- No JS changes were required — the existing `sortFilter` change handler already reads `e.target.value` and sets `state.sort` correctly
