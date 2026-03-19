# Add Location Field to Product Modal

**Date:** 2026-03-19

## Summary
Added the warehouse location (คลัง) field to the product detail modal so users can see where a product is stored without leaving the modal.

## Changes

### `index.html`
- Added a new `detail-item` with id `modal-location` in the modal's `.detail-grid`, after Sale Price.

### `app.js`
- Registered `modalLocation` element reference (`document.getElementById('modal-location')`).
- In `openModalInternal()`, populated the field with `product.locations || '-'`.
