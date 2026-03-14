# CHANGELOG: Product Modal Arrow Key Image Navigation

**Date:** 2026-03-12

---

## Change

Added **ArrowLeft / ArrowRight** keyboard support in the product modal to cycle through product images.

### Behavior
- **ArrowLeft**: Move to the previous image (wraps around from first → last)
- **ArrowRight**: Move to the next image (wraps around from last → first)  
- Does nothing if the product has only one image or no images
- Does not interfere with text inputs/textareas (existing guard)
- Existing **ArrowUp / ArrowDown** still navigate between products

### File Changed

#### `app.js`
- Added `ArrowLeft` / `ArrowRight` handlers inside the existing `document.addEventListener('keydown', ...)` block (~line 568)
- Finds all `.gallery-thumb` elements in the thumbnail strip, determines the currently `.active` one, calculates the new index with wrapping, and triggers `.click()` on the target thumbnail (reuses existing click logic)
