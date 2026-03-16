# Custom Product Image Upload Feature

**Date**: 2026-03-16
**Files Modified**: `config.ini`, `build_db.py`, `server.py`, `app.js`, `index.html`, `index.css`

## Summary

Added a custom product photo upload system that allows employees to upload real inventory photos. These custom photos are displayed as the **primary tier** in the gallery, replacing the copyright-restricted scraped images as the first photos shown.

## Image Tier Hierarchy (new)

1. **📷 Custom** – Employee-uploaded photos of real inventory (safe to share with customers)
2. **🏭 Official** – Scraped from manufacturer sites (copyright restricted)
3. **🌐 Web** – Scraped from Google Images (copyright restricted)

Admin can toggle official and web tiers on/off via admin panel.

## Configuration Changes (`config.ini`)

- Added `custom_dir = product_images` under `[images]` – directory for custom photos
- Added `[permissions]` section:
  - `custom_image_upload = admin,viewer` – who can upload
  - `custom_image_delete = admin,viewer` – who can delete
  - `show_official_images = yes` – toggle official tier visibility
  - `show_web_images = yes` – toggle web tier visibility

## Server Changes (`server.py`)

### New API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/products/<sku>/images/upload` | Upload custom images (multipart, with optional comment) |
| DELETE | `/api/products/<sku>/images/custom` | Delete a custom image |
| GET | `/api/permissions` | Get current permission settings |
| POST | `/api/permissions` | Update permission settings (admin only) |
| GET | `/images/custom/<path>` | Serve custom image files |

### Modified Endpoints
- **`GET /api/products/<sku>/images`** – Now returns `{ images: [...], permissions: {...} }` instead of flat array. Each image has `url`, `source` (custom/official/web), `filename`, `comment`, `uploaded_by`, `uploaded_at`.

### Helpers Added
- `_load_permissions()` / `_save_permissions()` – read/write permissions from config.ini
- `_check_permission(action)` – check if current user has permission
- `_get_custom_image_dir_for_sku(sku)` – resolve SKU folder path
- `_load_custom_metadata()` / `_save_custom_metadata()` – manage `_metadata.json` per SKU folder

### Image Processing
- Auto-resize to max 1200px using Pillow (if available), falls back to raw save
- EXIF orientation auto-correction (for mobile camera photos)
- RGBA/PNG to RGB/JPEG conversion at 85% quality
- Timestamped filenames to avoid collisions

## Frontend Changes

### `app.js`
- `fetchProductImages()` – handles new categorized API response with permissions
- `insertThumbnail()` – shows source badges, delete buttons on custom images, click updates caption bar
- `_updateCaptionBar()` – displays comment, uploader, date for current image
- `_setupUploadHandlers()` – file picker → preview → comment → upload flow
- `deleteCustomImage()` – deletes custom images with confirmation
- `refreshGallery()` – re-fetches and re-renders with permissions
- `_loadImagePermissions()` – admin panel: loads/saves permission settings via API

### `index.html`
- Added image caption bar below thumbnails
- Added upload button with camera icon and hidden file input
- Added upload dialog with preview grid, comment field, and progress bar
- Added admin panel "Image Permissions" section with tier toggles and role checkboxes

### `index.css`
- Gallery source badges (📷/🏭/🌐), delete buttons, custom thumbnail highlight
- Caption bar styling
- Upload button, dialog, preview grid, progress bar styles

## File Storage

Custom images are stored at: `product_images/<part_code>_<suffix>/`
- Example: `product_images/04111-20220-71_R/20260316_122300_1.jpg`
- Metadata in `product_images/<part_code>_<suffix>/_metadata.json`
