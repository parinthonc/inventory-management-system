# Camera Button Fix in Product Modal

**Date:** 2026-03-19

## Problem
On mobile devices, pressing "ถ่ายรูป / เลือกรูป" in the product modal always opened the **file picker** instead of the **camera app**. This is because the `<input type="file">` element lacked the `capture` attribute.

## Solution
Split the single button into **two separate buttons**:

| Button | Label | Behavior |
|--------|-------|----------|
| `#btn-take-photo` | 📷 ถ่ายรูป | Opens the **camera** directly on mobile (uses `capture="environment"`) |
| `#btn-upload-photo` | 🖼 เลือกรูป | Opens the **file picker / gallery** (no `capture` attribute) |

## Files Changed

### `index.html`
- Replaced single `#btn-upload-photo` button with two buttons: `#btn-take-photo` and `#btn-upload-photo`
- Added a second hidden file input `#camera-image-input` with `capture="environment"` attribute
- Original file input `#custom-image-input` remains for gallery/file picker use

### `app.js`
- Updated `_setupUploadHandlers()` to wire up both buttons
- `#btn-take-photo` triggers `#camera-image-input` (camera)
- `#btn-upload-photo` triggers `#custom-image-input` (gallery)
- Extracted shared `_handleFileInputChange()` function to avoid code duplication
- Both inputs feed into the same upload preview and workflow
