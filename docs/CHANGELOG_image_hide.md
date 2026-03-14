# CHANGELOG: Image Hide/Unhide Feature
**Date**: 2026-03-13

## Summary
Added ability for users to hide incorrect product images from the gallery by pressing a trash button. Images are renamed with a `_hidden_` prefix (not deleted), making them invisible to the webapp but easily recoverable.

## Changes

### Backend (`server.py`)
- **`serve_image()`**: Blocks serving files with `_hidden_` prefix (returns 404)
- **`_find_images_in_dir()`**: Filters out `_hidden_` prefixed files from gallery listings
- **`_resolve_image_dir(sku)`**: New helper function that resolves the image folder path(s) for a given SKU, handling R-suffix stripping and both primary/secondary directories with first-token matching
- **`POST /api/products/<sku>/images/hide`**: Accepts `{ "filename": "photo.jpg" }`, renames the file to `_hidden_photo.jpg`
- **`POST /api/products/<sku>/images/unhide`**: Accepts `{ "filename": "_hidden_photo.jpg" }`, restores original filename
- **`GET /api/products/<sku>/images/hidden`**: Returns list of hidden images for a product

### Backend (`build_db.py`)
- **`_find_in_dir()`**: Filters out `_hidden_` prefixed files when building thumbnail list, so hidden images don't appear as grid thumbnails

### Frontend (`app.js`)
- **`insertThumbnail()`**: Now sets `data-filename` on the main image when a thumbnail is clicked, so the trash button knows which file to hide
- **Main image trash button**: A 32px red trash icon button positioned at the top-right of the main image, visible on hover only
- **`hideImage(filename)`**: Calls hide API with confirmation dialog, then refreshes gallery
- **`unhideImage(hiddenName)`**: Calls unhide API, then refreshes gallery
- **`refreshGallery()`**: Re-fetches and re-renders the gallery after hide/unhide
- **`loadHiddenImages()`**: Fetches hidden images and displays them dimmed with restore buttons
- **`insertHiddenToggle()`**: Adds "👁 Show hidden" toggle below thumbnail strip

### Frontend (`index.css`)
- New styles: `.gallery-thumb-wrapper`, `.gallery-trash-btn`, `.gallery-restore-btn`, `.gallery-thumb.hidden-img`, `.gallery-hidden-toggle`

## How It Works
1. User opens a product modal and sees images in the gallery
2. Hovering over a thumbnail reveals a red `✕` button
3. Clicking the trash button shows a confirmation dialog (bilingual TH/EN)
4. On confirm, the file is renamed from `photo.jpg` → `_hidden_photo.jpg` on disk
5. Gallery refreshes immediately, hiding the removed image
6. A "👁 Show hidden" toggle below thumbnails lets users view hidden images (dimmed, with ↩ restore button)
7. Clicking restore reverses the rename
