# Remove Front Login Page

**Date:** 2026-03-16  
**Summary:** Removed the mandatory login page so users go straight to the app. Users are auto-logged in as guest. A Login button in the header allows upgrading to authenticated accounts.

## Changes

### `app.js`
- `authCheckAndInit()` – No longer blocks the app behind a login overlay. Auto-logs in as `guest` if no session exists.
- Added `_autoGuestLogin()` – Silently authenticates as guest.
- Added `_showLoginOverlay()` – Opens the login overlay on demand from the header.
- `_showUserUI()` – Shows a Login button (🔑) for guest users; hides logout for guests. Shows logout for non-guest users.
- Login form submit & guest login handlers – Now `location.reload()` on success instead of manual re-init, ensuring clean UI reset.

### `index.html`
- Added `#login-header-btn` in the navbar (between user badge and admin button) – a Login icon button, hidden by default, shown for guests.

## Behavior
| Scenario | Before | After |
|----------|--------|-------|
| First visit | Login overlay blocks app | App loads immediately as guest |
| Guest user | Must click "Login as Guest" | Auto-logged in, sees Login button in header |
| Login as admin | Via login overlay | Click Login button in header → overlay appears |
| After login | Form manually re-inits app | Page reloads with new session |
| Logout | Page reloads (shows login) | Page reloads (auto-guest login) |
