# Changelog: Browser Back Button Navigation

**Date:** 2026-03-11  
**Scope:** Entire web app navigation (tabs, modals, detail views)

## Summary

Implemented comprehensive hash-based browser history navigation using the History API (`pushState`/`popstate`). Every navigation action now creates a history entry so the browser back/forward buttons work intuitively throughout the entire app.

## Hash Routing Scheme

| Hash                    | View                        |
|-------------------------|-----------------------------|
| `#products`             | Products tab (default)      |
| `#moves`                | Stock Moves tab             |
| `#flags`                | Flags tab                   |
| `#customer`             | Customer list               |
| `#invoice`              | Invoice tab                 |
| `#product/<sku>`        | Product modal overlay       |
| `#customer/<code>`      | Customer detail view        |
| `#invoice/<number>`     | Invoice detail view         |

## Key User Flows

### Product Modal → Customer Detail → Back
1. User opens a product modal → hash becomes `#product/<sku>`
2. User clicks a customer hyperlink (from/to field) → hash becomes `#customer/<code>`
3. User presses browser back → returns to `#product/<sku>` → product modal reopens

### Tab Navigation → Detail → Back
1. User navigates to customer tab → hash `#customer`
2. User opens customer detail → hash `#customer/<code>`
3. User presses browser back → returns to `#customer` → shows customer list

### Same pattern works for Invoice, Flags, etc.

## Architecture Changes

### New Functions
- `navPush(hash)` — pushes a new history entry (deduplicates)
- `navReplace(hash)` — replaces current history entry
- `handleNavigation()` — central router that reads `location.hash` and renders the correct view
- `switchTabInternal(tabName)` — internal tab switch without pushing history (used by popstate router)
- `openCustomerDetailInternal(code)` — internal customer detail open without pushing history

### Modified Functions
- `switchTab()` — now pushes hash before switching tab
- `openModal()` — pushes `#product/<sku>` instead of generic `#product`
- `closeModal()` — checks `#product/` prefix and calls `history.back()`
- `openCustomerDetail()` — pushes `#customer/<code>` then delegates to internal
- `openInvoiceDetail()` — pushes `#invoice/<number>`
- Customer back button — now calls `history.back()` instead of manually resetting state
- Invoice back button — now calls `history.back()` instead of manually resetting state
- From/to customer link click handler — closes modal visually, uses `switchTabInternal` + `openCustomerDetail` (which pushes its own hash)
- `popstate` handler — replaced with unified `handleNavigation()` call
- `init()` — sets initial hash on load and restores state from hash on refresh

### Guard Flag
- `_handlingPopstate` — prevents re-entrant `navPush` calls when the popstate handler is processing a browser-back event

## Files Modified
- `app.js` — All navigation functions listed above
