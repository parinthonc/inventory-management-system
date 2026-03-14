# Changelog: Remove Customer Columns

**Date:** 2026-03-11  
**Scope:** Customer modal & ประวัติลูกค้า tab

## Summary

Removed several fields/columns from the customer section as they were deemed unnecessary.

## Changes Made

### 1. Customer Detail Modal (`app.js` — `openCustomerDetail()`)
- **Removed** `ยอดขายประจำปี` (annual sales value) detail item
- **Removed** `ยอดรับชำระ` (annual receipts value) detail item
- Cleaned up the unused `salesVal`, `salesFormatted`, `receiptsVal`, `receiptsFormatted` variables

### 2. Customer List Table — ประวัติลูกค้า tab (`index.html`)
- **Removed** `ยอดขายปี` column header from the table
- **Removed** `ใบกำกับล่าสุด` column header from the table

### 3. Customer List Rows (`app.js` — `renderCustomers()`)
- **Removed** the sales value `<td>` cell (`salesFormatted`)
- **Removed** the last invoice `<td>` cell (`lastInvHtml`)
- Cleaned up unused variables: `salesVal`, `salesFormatted`, `lastInv`, `lastInvNo`, `lastInvHtml`
- Updated all `colspan` attributes from `8` to `6` across customer-related loading/empty/error states

## Files Modified
- `index.html` — lines ~441-454 (customer list table header & spinner colspan)
- `app.js` — `fetchCustomers()`, `renderCustomers()`, `openCustomerDetail()` functions
