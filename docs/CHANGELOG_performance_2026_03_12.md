# Performance Optimization - Remove backdrop-filter blur

**Date:** 2026-03-12  
**File changed:** `index.css`

## Summary
Removed all `backdrop-filter: blur()` CSS effects to improve rendering performance on old/low-RAM client computers.

## What changed
Removed `backdrop-filter` and `-webkit-backdrop-filter` from 4 locations:

| Class | Old | New | Reason |
|-------|-----|-----|--------|
| `.glass` | `blur(12px)` | Removed | Applied to 10+ cards across all tabs |
| `.navbar` | `blur(16px)`, opacity 0.8 | Removed, opacity raised to 0.95 | Always visible, recalculated on scroll |
| `.modal-nav-controls` | `blur(8px)`, opacity 0.5 | Removed, opacity raised to 0.7 | Inside product detail modal |
| `.sync-status-bar` | `blur(16px)`, opacity 0.92 | Removed, opacity raised to 0.97 | Always visible at bottom of page |

## Why
`backdrop-filter: blur()` forces the browser's compositor to re-render blurred layers on every frame during scrolling and animations. On old PCs without GPU hardware acceleration, this causes visible lag. Removing it gives significant performance improvement with minimal visual difference.

## Visual impact
- Background opacity was increased on affected elements to compensate for the loss of blur (more opaque = less see-through = still looks clean)
- The dark theme still looks great, just without the frosted-glass blur effect
