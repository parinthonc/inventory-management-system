# Changelog: Thai Font Readability Improvement

**Date:** 2026-03-14  
**Summary:** Added Sarabun font for Thai text with size-adjust to visually match Inter.

---

## Problem

The app used **Inter** as its only loaded web font. Inter does not contain Thai glyphs, so the browser fell back to the OS default Thai font (Leelawadee UI on Windows), which appeared noticeably smaller and thinner compared to Inter's tall x-height and sturdy weight.

## Solution

### Approach: `@font-face` with `size-adjust`

We load **Sarabun** (Thai-optimized font) from Google Fonts CDN using our own `@font-face` declarations with two key adjustments:

1. **`size-adjust: 112%`** — Scales Sarabun up by 12% so its visual height matches Inter's larger metrics
2. **`unicode-range: U+0E00-0E7F`** — Only activates for Thai glyphs, so Latin text continues using Inter untouched

### Files Changed

#### `index.css` (top of file)
- Added 5 `@font-face` blocks for `'Sarabun Adjusted'` (weights 300-700)
- Each uses the Thai-subset woff2 URL from Google Fonts CDN (v17)
- Applied `size-adjust: 112%` and `unicode-range` limited to Thai Unicode block
- Updated `--font-sans` to: `'Inter', 'Sarabun Adjusted', 'Sarabun', ...`

#### `index.html`
- Google Fonts `<link>` loads **Inter only** (Sarabun is loaded separately via CSS `@font-face`)

## How It Works

```
Font stack: Inter → Sarabun Adjusted → Sarabun → system fallbacks

For Latin characters (A-Z, 0-9):
  → Inter has the glyphs → rendered by Inter

For Thai characters (ก-ฮ, vowels, tone marks):
  → Inter doesn't have them
  → 'Sarabun Adjusted' has them (unicode-range match)
  → Rendered at 112% size via size-adjust → visually matches Inter
```

## Why This Approach?

| Approach | Problem |
|----------|---------|
| Just add Sarabun to font stack | Thai appears ~15% smaller than Inter |
| Increase Thai font-size via CSS | Can't target Thai characters specifically |
| Use `local()` in @font-face | Only works if Sarabun is installed on OS |
| **`@font-face` + `url()` + `size-adjust`** | ✅ Works everywhere, precise control |

## Technical Notes

- The woff2 URLs point to Google Fonts CDN v17 Thai subset
- `unicode-range` ensures the font file is only downloaded when Thai glyphs are needed (efficient)
- `size-adjust` is a CSS descriptor supported in all modern browsers (Chrome 92+, Firefox 92+, Safari 17+)
- The `112%` value was determined by comparing Inter and Sarabun visual metrics
