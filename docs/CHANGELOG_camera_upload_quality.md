# Fix: Camera Upload Producing Low Resolution Photos (60-70 KB)

**Date:** 2026-03-19  
**Issue:** Photos taken via the webapp's camera on mobile devices were only 60-70 KB with very low resolution, instead of the expected 2-8 MB from the native camera app.

## Root Cause

The HTML `capture="environment"` attribute on file inputs was forcing mobile browsers to use their **built-in low-resolution camera capture** instead of delegating to the device's native camera app. The native camera app produces full-resolution photos (2-8 MB), but the browser's inline capture produces tiny compressed images (~60-70 KB).

## Changes Made

### `index.html`
- **Line 1133**: Removed `capture="environment"` from the `#custom-image-input` file input (modal upload button).

### `app.js`
- **Lines 844-846**: Removed the `capture="environment"` attribute that was conditionally set on the photo flags file input for mobile devices.

## Behavior After Fix

- On mobile: tapping the upload button opens a file picker where the user can choose **"Camera"** (opens native camera app → full-res photos) or **"Files/Gallery"**
- On desktop: unchanged — still opens the normal file picker
- The server-side resize (max 1200px, JPEG quality 85) still applies, producing reasonable ~200-500 KB final images from full-res originals

## Notes

- The server-side `MAX_IMAGE_DIMENSION = 1200` and JPEG quality 85 compression in `server.py` is separate and reasonable — it was NOT the cause of the 60-70 KB issue
- The `MAX_IMAGE_SIZE = 10 MB` upload limit remains unchanged
