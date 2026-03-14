# Changelog

## 2026-03-11 — Fix: Resolve Button in "รายการของไม่ตรงหน้าเครื่อง" Tab

### Problem
Clicking the **Resolve** button in the flags tab (`รายการของไม่ตรงหน้าเครื่อง`) was incorrectly opening the **product detail modal** instead of triggering the unflag/resolve action.

### Root Cause
Two compounding bugs in `app.js`:

1. **Broken per-render listeners** — `renderFlags()` was using `document.querySelectorAll('.unflag-btn').forEach(btn => btn.addEventListener(...))` to attach click listeners after every render. However, because the table is re-rendered via `innerHTML`, the freshly created button elements lose their listeners on the next render cycle, meaning the `e.stopPropagation()` call never fired for already-rendered buttons.

2. **Event bubbling order** — Even with a corrected delegated listener on the `<tbody>`, `tr.onclick` fires *before* the delegated handler because bubbling travels from child to parent. `stopPropagation()` in the tbody's handler was therefore too late to stop `tr.onclick`.

### Fix (both changes in `app.js`)

1. **`setupEventListeners()`** — Replaced the per-render `querySelectorAll` approach with a **single delegated event listener** attached once to `els.flagsList` (`<tbody>`). Uses `e.target.closest('.unflag-btn')` to identify resolve-button clicks and handles them there.

2. **`renderFlags()`** — Changed `tr.onclick` from:
   ```js
   tr.onclick = () => openModal(f, idx);
   ```
   to:
   ```js
   tr.onclick = (e) => { if (e.target.closest('.unflag-btn')) return; openModal(f, idx); };
   ```
   This ensures that clicks originating from the Resolve button are ignored by the row handler, and the delegated listener alone handles the unflag logic.

### Files Changed
- `app.js`
  - `setupEventListeners()` lines ~597–603: delegated unflag handler added on `els.flagsList`
  - `renderFlags()` line ~2223: `tr.onclick` updated to early-return on `.unflag-btn` clicks
  - `renderFlags()` lines ~2242–2264: removed stale per-render `querySelectorAll` listener block
