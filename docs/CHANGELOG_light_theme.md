# Changelog — Light Theme Mode

**Date:** 2026-03-15

## Summary
Added a light theme option for users who have difficulty reading text on a dark background. The theme preference persists across sessions via `localStorage`.

## Changes

### `index.css`
- Added `[data-theme="light"]` block after `:root` with overrides for all CSS custom properties (`--bg-main`, `--text-primary`, `--border-color`, etc.)
- Added ~80 selectors overriding hardcoded `rgba()`/hex dark colors throughout the app (navbar, glass cards, modals, tables, inputs, buttons, badges, sync bar, tooltips, flags, spinners, etc.)
- Added `#theme-toggle-btn` styling (circular button with hover rotation effect)
- Added smooth CSS transitions for theme switching

### `index.html`
- Added theme toggle button inside the navbar `.stats` div (after the Total SKUs badge)
- Button contains sun icon (visible in dark mode) and moon icon (visible in light mode)

### `app.js`
- Added IIFE at the top of the file that immediately reads `localStorage('theme')` and sets `data-theme` attribute on `<html>` to prevent flash of wrong theme
- On `DOMContentLoaded`, syncs the sun/moon icon visibility and attaches the click handler
- Click handler toggles between `dark` and `light`, saves to `localStorage`, and swaps icons

## How It Works
- Default theme: **dark** (existing behavior unchanged)
- Click the ☀️ (sun) button in the navbar → switches to **light** theme
- Click the 🌙 (moon) button → switches back to **dark** theme
- Preference is saved in `localStorage` and restored on page load
