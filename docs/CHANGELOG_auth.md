# CHANGELOG — User Authentication System (Phase 1)
**Date:** 2026-03-15

## Summary
Added a complete user authentication system to the inventory management application.
Users must now log in before accessing any data or API endpoints.

## What Changed

### New Features
- **Login page** — Full-screen overlay with username/password fields, gradient UI, company branding
- **"Login as Guest" button** — One-click access for viewers without typing credentials
- **Session management** — 30-day persistent sessions using Flask signed cookies
- **User management admin panel** — Add/delete users, reset passwords, change own password
- **Audit logging** — All login/logout events logged with timestamps and IP addresses
- **Route protection** — All API endpoints return 401 if not authenticated

### Default Accounts (created on first run)
| Username | Password | Role |
|----------|----------|------|
| `admin` | `admin` | admin |
| `guest` | `guest` | viewer |

> ⚠️ Change the default admin password after first login!

### Files Modified
- `server.py` — Auth tables, session config, auth endpoints, global route protection
- `index.html` — Login overlay, admin modal, navbar buttons
- `index.css` — Login/admin styles (dark + light theme)
- `app.js` — Auth check on load, login/logout handlers, admin panel JS
- `.gitignore` — Added `auth_secret.key`

### New Files (auto-generated at runtime)
- `auth_secret.key` — Flask session secret (auto-generated, git-ignored)
- `users` table in `inventory.db`
- `audit_log` table in `inventory.db`

## Phase 2 (Future)
- Role-based data restrictions (hide unit cost, quantities from viewer role)
- Granular permissions per data section
