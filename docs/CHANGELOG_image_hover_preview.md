# Image Hover Preview Feature

**Date:** 2026-03-13  
**Files Modified:** `app.js`, `index.css`

## Summary

Added a hover preview feature that displays a full-size version of the product image 
when the user hovers their cursor over:
1. A **thumbnail** in the product list table (400×400px preview)
2. The **main image** in the product detail modal (600×600px preview)

## How It Works

1. **On hover** over a `.thumb-cell` (product list) or the modal main image, 
   a floating preview panel appears near the cursor showing the full-size image.
2. **The preview follows the cursor** as it moves, staying within viewport bounds.
3. **On mouse leave**, the preview fades away smoothly.
4. **On modal close**, the preview is automatically hidden via a MutationObserver.

## Resource Impact

- **Zero extra network requests** — the preview reuses the same image URL that is 
  already loaded and cached by the browser.
- **Pure CSS transitions** — uses GPU-accelerated `opacity` and `transform` for smooth 
  animations with no JavaScript animation overhead.
- **Single DOM element** — only one preview `<div>` is created and reused for all images.
- **Event delegation** — uses a single set of event listeners on the table body instead 
  of attaching listeners to each row.

## Changes

### `app.js`
- Rewrote `initImageHoverPreview()` IIFE to handle both product list thumbnails and 
  modal main image
- Added `showPreview()` / `hidePreview()` helpers with size class parameter
- Product list thumbs use `preview-sm` (400×400px), modal image uses `preview-lg` (600×600px)
- Added MutationObserver to auto-hide preview when modal closes

### `index.css`
- Added `.image-hover-preview` base styles (fixed position, border, shadow, transitions)
- Added `.preview-sm` and `.preview-lg` size variant classes
- Added `cursor: zoom-in` on `.main-image-container img` to hint hover-to-zoom
