# Full Quality Photo Upload

**Date:** 2026-03-19

## Problem
Photos uploaded via the webapp were being saved at only 60-70 KB, even when the original file was 2-8 MB from the phone camera. This resulted in low-resolution images in the product image folders.

## Root Cause
Two factors contributed:
1. **Server-side resize**: `MAX_IMAGE_DIMENSION` was set to `1200` px, shrinking typical phone photos (~4000×3000) to ~1200×900 — an 11× pixel reduction.
2. **JPEG re-encoding** at quality `85` with `optimize=True` further compressed the already-resized image.
3. **`capture="environment"` attribute** on the modal file input forced some mobile browsers to use a low-res inline camera instead of the native camera app.

## Changes

### `server.py`
- Changed `MAX_IMAGE_DIMENSION` from `1200` to `0` (disabled resize — full original resolution preserved)
- Changed JPEG save quality from `85` to `95`
- Resize logic now skips entirely when `MAX_IMAGE_DIMENSION = 0`
- Thumbnails (300px) still generated separately for fast UI loading

### `index.html`
- Removed `capture="environment"` from the modal file input (`#custom-image-input`), so mobile browsers open the native camera app which produces full-resolution photos

## Notes
- The `MAX_IMAGE_SIZE` limit remains at **10 MB** per file
- Thumbnails (`_thumb_*` files) are unaffected — still 300px max at quality 75
- To re-enable resize in the future, set `MAX_IMAGE_DIMENSION` to desired pixel cap (e.g. `2400`)
