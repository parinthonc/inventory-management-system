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
- Example: `product_images/04111-20220-71_R/20260316_122300_a1b2c3d4.jpg`
- Metadata in `product_images/<part_code>_<suffix>/_metadata.json`

## Bug Fixes (2026-03-16)

### 1. Race condition in filename generation (server.py)
- **Before**: Filenames used sequential numbering (`_1.jpg`, `_2.jpg`) based on `os.listdir()` count. Two concurrent uploads in the same second could generate the same filename, causing silent data loss.
- **After**: Filenames use UUID suffix (`_a1b2c3d4.jpg`) for guaranteed uniqueness.

### 2. Fragile EXIF orientation handling (server.py)
- **Before**: Used deprecated `img._getexif()` and a fragile `for` loop to find the orientation key. If the key were missing from Pillow's tag dict, the wrong EXIF tag would be read, potentially causing incorrect image rotation.
- **After**: Replaced with Pillow's built-in `ImageOps.exif_transpose(img)` which handles all orientation cases correctly.

### 3. Inconsistent `_check_permission` return value (server.py)
- **Before**: Returned a 2-tuple `(True, None)` on success and a 3-tuple on failure, with callers using `len(perm_result) > 2` to handle the discrepancy.
- **After**: Always returns a 3-tuple `(allowed, response, status_code)` for consistent, clearer handling.

## New Features (2026-03-16)

### 1. Batch upload with "เพิ่มรูป / Add More Photos" (index.html, app.js, index.css)
- After selecting/capturing a photo, the upload preview dialog now shows an "เพิ่มรูป / Add More Photos" button
- Tapping this button re-opens the camera/file picker to add more photos to the batch
- Photos accumulate in the preview area; the Upload button shows count (e.g. "อัปโหลด (3 รูป)")
- All accumulated photos are uploaded in a single request when "อัปโหลด" is tapped
- This enables mobile users to take multiple camera photos one-by-one before uploading all at once
- UI labels changed to Thai (ถ่ายรูป/เลือกรูป, เพิ่มรูป, อัปโหลด, ยกเลิก, คำอธิบาย)

### 2. Full-size image hover preview (app.js, index.css)
- **Before**: Hovering over the modal's main image showed a preview capped at 600×600px
- **After**: Preview now uses up to 90% of viewport (90vw × 90vh) and centers on screen
- Product list thumbnail hover preview still follows the cursor at 400×400px
