# CHANGELOG: Database Backup System

**Date:** 2026-03-15

## Summary
Added an automated and manual database backup system with one-click restore,
daily scheduling, and a management UI inside the admin panel.

## Changes

### Backend (`server.py`)
- **Backup engine:** Uses SQLite's `backup()` API for safe, consistent copies
  even while the database is in use. Falls back to `shutil.copy2()` if needed.
- **API endpoints** (all admin-only):
  - `POST /api/admin/backup` — create a timestamped backup
  - `GET /api/admin/backups` — list all backups with size, date, type
  - `POST /api/admin/backup/restore` — restore from a backup (creates safety backup first)
  - `DELETE /api/admin/backup/<filename>` — delete a specific backup
  - `GET /api/admin/backup/download/<filename>` — download a backup file
  - `GET/POST /api/admin/backup/schedule` — toggle auto-backup on/off
- **Auto-backup scheduler:** Background thread checks every hour, creates one
  daily backup if none exists for today. Starts 30s after server boot.
- **Retention policy:** Keeps max 30 backups (configurable), auto-deletes oldest.
  Pre-restore safety backups are excluded from this count.
- **Path traversal protection:** All filenames are sanitized with `os.path.basename()`.
- **Audit logging:** All backup operations (create, restore, delete, download,
  schedule changes) are recorded in the audit log.

### Frontend
- **Admin panel UI** (`index.html`): Added "Database Backups" section with:
  - "Create Backup Now" button
  - "Auto Daily" toggle switch
  - Backup table (filename, size in MB, creation date, actions)
  - Restore / Download / Delete action buttons per backup
  - Inline status messages with auto-dismiss
- **JavaScript** (`app.js`): Backup management functions for list, create,
  restore, download, delete, and auto-toggle operations.
- **CSS** (`index.css`): Toggle switch styles for the auto-backup control.

### Configuration
- **`config.ini`**: Added `[backup]` section with `backup_dir`, `max_backups`,
  and `auto_backup` settings.
- **`.gitignore`**: Added `backups/` directory.

## Backup File Format
- **Location:** `backups/` directory (relative to project root)
- **Naming:** `inventory_YYYY-MM-DD_HH-MM-SS.db`
- **Safety backups:** `pre_restore_YYYY-MM-DD_HH-MM-SS.db` (created before any restore)
