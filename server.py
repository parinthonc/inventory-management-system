from flask import Flask, jsonify, request, send_from_directory, Response, session
import sqlite3
import os
import math
import re
import tempfile
import shutil
import csv
import json
import datetime
import subprocess
import threading
import time
import queue
import secrets
import functools
from collections import defaultdict
import builtins
from werkzeug.security import generate_password_hash, check_password_hash

# Override built-in print to prepend a timestamp to every console message
_original_print = builtins.print

def _timestamped_print(*args, **kwargs):
    """Wrapper around print() that prefixes output with [HH:MM:SS] timestamp."""
    timestamp = datetime.datetime.now().strftime('[%H:%M:%S]')
    _original_print(timestamp, *args, **kwargs)

builtins.print = _timestamped_print

app = Flask(__name__, static_folder='.', static_url_path='')

# ─── Flask Session Secret Key ─────────────────────────────────────────────────
# Auto-generate a secret key and persist it so sessions survive server restarts.
AUTH_SECRET_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'auth_secret.key')

def _load_or_create_secret_key():
    """Load secret key from file, or generate and save a new one."""
    if os.path.isfile(AUTH_SECRET_FILE):
        with open(AUTH_SECRET_FILE, 'r') as f:
            return f.read().strip()
    key = secrets.token_hex(32)
    with open(AUTH_SECRET_FILE, 'w') as f:
        f.write(key)
    print(f"[Auth] Generated new secret key -> {AUTH_SECRET_FILE}")
    return key

app.secret_key = _load_or_create_secret_key()

# Import build_db functions and config
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_db import (SUFFIX_MAP, find_thumbnail,
                      IMAGE_DIRS, IMAGE_DIR, IMAGE_DIR_PRIMARY, IMAGE_DIR_SECONDARY,
                      PRIMARY_MATCH_FIRST_TOKEN, SECONDARY_MATCH_FIRST_TOKEN,
                      _primary_folder_map, _secondary_folder_map, LOGO_FILE, ARCHIVED_LEDGER_DIR)

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inventory.db')
INVOICE_DIR = os.path.join(os.path.dirname(__file__), 'invoice')

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_flags_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_flags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT NOT NULL,
            flag_type TEXT NOT NULL,
            note TEXT DEFAULT '',
            flagged_at TEXT DEFAULT (datetime('now', 'localtime')),
            flagged_by TEXT DEFAULT '',
            UNIQUE(sku)
        )
    ''')
    # Migration: add flagged_by column if it doesn't exist yet
    try:
        cursor.execute("ALTER TABLE stock_flags ADD COLUMN flagged_by TEXT DEFAULT ''")
        print('[Migration] Added flagged_by column to stock_flags')
    except Exception:
        pass  # Column already exists
    conn.commit()
    conn.close()

init_flags_table()

# ─── Authentication System ────────────────────────────────────────────────────

def init_auth_tables():
    """Create users and audit_log tables if they don't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'viewer',
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            action TEXT NOT NULL,
            ip_address TEXT,
            timestamp TEXT DEFAULT (datetime('now', 'localtime'))
        )
    ''')
    conn.commit()
    conn.close()

init_auth_tables()


def _create_default_accounts():
    """Create default admin and guest accounts if no users exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as cnt FROM users')
    count = cursor.fetchone()['cnt']
    if count == 0:
        cursor.execute(
            'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
            ('admin', generate_password_hash('admin'), 'admin')
        )
        cursor.execute(
            'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
            ('guest', generate_password_hash('guest'), 'viewer')
        )
        conn.commit()
        print('[Auth] ⚠️  Created default accounts: admin/admin and guest/guest')
        print('[Auth] ⚠️  CHANGE THE DEFAULT ADMIN PASSWORD after first login!')
    conn.close()

_create_default_accounts()


def login_required(f):
    """Decorator to protect routes — returns 401 if not authenticated."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Decorator to restrict routes to admin users only."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        if session.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated


def _log_audit(username, action, ip_address=None):
    """Write an entry to the audit log."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO audit_log (username, action, ip_address) VALUES (?, ?, ?)',
            (username, action, ip_address or '')
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f'[Auth] Audit log error: {e}')


# ── Auth API Endpoints ────────────────────────────────────────────────────────

@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    """Authenticate user and create session."""
    data = request.get_json(force=True)
    username = (data.get('username') or '').strip().lower()
    password = data.get('password') or ''

    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user['password_hash'], password):
        session['user'] = user['username']
        session['role'] = user['role']
        session['user_id'] = user['id']
        session.permanent = True
        app.permanent_session_lifetime = datetime.timedelta(days=30)
        _log_audit(username, 'login', request.remote_addr)
        print(f"[Auth] Login: {username} (role={user['role']}) from {request.remote_addr}")
        return jsonify({
            'success': True,
            'user': {'username': user['username'], 'role': user['role']}
        })
    else:
        _log_audit(username, 'login_failed', request.remote_addr)
        print(f"[Auth] Failed login attempt: {username} from {request.remote_addr}")
        return jsonify({'error': 'Invalid username or password'}), 401


@app.route('/api/auth/logout', methods=['POST'])
def auth_logout():
    """Clear the user session."""
    username = session.get('user', 'unknown')
    _log_audit(username, 'logout', request.remote_addr)
    session.clear()
    print(f"[Auth] Logout: {username}")
    return jsonify({'success': True})


@app.route('/api/auth/me')
def auth_me():
    """Return the current authenticated user info, or 401."""
    if 'user' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    return jsonify({
        'username': session['user'],
        'role': session['role']
    })


@app.route('/api/auth/change-password', methods=['POST'])
@login_required
def auth_change_password():
    """Allow the current user to change their own password."""
    data = request.get_json(force=True)
    current_pw = data.get('current_password', '')
    new_pw = data.get('new_password', '')

    if not current_pw or not new_pw:
        return jsonify({'error': 'Current and new password required'}), 400
    if len(new_pw) < 3:
        return jsonify({'error': 'Password must be at least 3 characters'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (session['user'],))
    user = cursor.fetchone()

    if not user or not check_password_hash(user['password_hash'], current_pw):
        conn.close()
        return jsonify({'error': 'Current password is incorrect'}), 401

    cursor.execute(
        'UPDATE users SET password_hash = ? WHERE id = ?',
        (generate_password_hash(new_pw), user['id'])
    )
    conn.commit()
    conn.close()
    _log_audit(session['user'], 'change_password', request.remote_addr)
    print(f"[Auth] Password changed: {session['user']}")
    return jsonify({'success': True})


# ── Admin API Endpoints ───────────────────────────────────────────────────────

@app.route('/api/admin/users', methods=['GET'])
@admin_required
def admin_list_users():
    """List all user accounts (without password hashes)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, role, created_at FROM users ORDER BY id')
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(users)


@app.route('/api/admin/users', methods=['POST'])
@admin_required
def admin_create_user():
    """Create a new user account."""
    data = request.get_json(force=True)
    username = (data.get('username') or '').strip().lower()
    password = data.get('password') or ''
    role = data.get('role', 'viewer')

    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    if role not in ('admin', 'viewer'):
        return jsonify({'error': 'Role must be admin or viewer'}), 400
    if len(password) < 3:
        return jsonify({'error': 'Password must be at least 3 characters'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
            (username, generate_password_hash(password), role)
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        _log_audit(session['user'], f'create_user:{username}:{role}', request.remote_addr)
        print(f"[Auth] User created: {username} (role={role}) by {session['user']}")
        return jsonify({'success': True, 'id': user_id})
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': f'Username "{username}" already exists'}), 409


@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@admin_required
def admin_delete_user(user_id):
    """Delete a user account."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT username FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'User not found'}), 404
    if user['username'] == session['user']:
        conn.close()
        return jsonify({'error': 'Cannot delete your own account'}), 400
    cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    _log_audit(session['user'], f'delete_user:{user["username"]}', request.remote_addr)
    print(f"[Auth] User deleted: {user['username']} by {session['user']}")
    return jsonify({'success': True})


@app.route('/api/admin/users/<int:user_id>/reset-password', methods=['POST'])
@admin_required
def admin_reset_password(user_id):
    """Reset a user's password (admin operation)."""
    data = request.get_json(force=True)
    new_pw = data.get('password', '')
    if not new_pw or len(new_pw) < 3:
        return jsonify({'error': 'Password must be at least 3 characters'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT username FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'User not found'}), 404
    cursor.execute(
        'UPDATE users SET password_hash = ? WHERE id = ?',
        (generate_password_hash(new_pw), user_id)
    )
    conn.commit()
    conn.close()
    _log_audit(session['user'], f'reset_password:{user["username"]}', request.remote_addr)
    print(f"[Auth] Password reset for {user['username']} by {session['user']}")
    return jsonify({'success': True})


@app.route('/api/admin/audit-log')
@admin_required
def admin_audit_log():
    """Return the last 100 audit log entries."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM audit_log ORDER BY id DESC LIMIT 100')
    entries = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(entries)


# ─── Database Backup System ──────────────────────────────────────────────────
# Provides manual and automated backups of inventory.db with restore capability.

import configparser as _configparser

_backup_config = _configparser.ConfigParser()
_backup_config.read(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini'))

BACKUP_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    _backup_config.get('backup', 'backup_dir', fallback='backups')
)
BACKUP_MAX = _backup_config.getint('backup', 'max_backups', fallback=30)
BACKUP_AUTO_ENABLED = _backup_config.getboolean('backup', 'auto_backup', fallback=True)

# Ensure backup directory exists
os.makedirs(BACKUP_DIR, exist_ok=True)

# In-memory toggle for auto-backup (persisted to config.ini on change)
_auto_backup_enabled = BACKUP_AUTO_ENABLED
_backup_timer = None
_BACKUP_CHECK_INTERVAL = 3600  # Check every hour


def _create_backup(prefix='inventory'):
    """Create a timestamped backup of the database and config files. Returns the backup filename."""
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    backup_filename = f'{prefix}_{timestamp}.db'
    backup_path = os.path.join(BACKUP_DIR, backup_filename)

    # Use SQLite backup API for a safe, consistent copy (even while DB is in use)
    try:
        src_conn = sqlite3.connect(DB_FILE)
        dst_conn = sqlite3.connect(backup_path)
        src_conn.backup(dst_conn)
        dst_conn.close()
        src_conn.close()
    except Exception:
        # Fallback to file copy if backup API fails
        shutil.copy2(DB_FILE, backup_path)

    print(f'[Backup] Created: {backup_filename} ({os.path.getsize(backup_path) / 1024 / 1024:.1f} MB)')

    # Also back up small config files alongside the DB
    _base_dir = os.path.dirname(os.path.abspath(__file__))
    _config_files = ['config.ini', 'auth_secret.key', 'sync_config.json']
    for cfg_name in _config_files:
        src = os.path.join(_base_dir, cfg_name)
        if os.path.isfile(src):
            dst = os.path.join(BACKUP_DIR, f'{prefix}_{timestamp}_{cfg_name}')
            try:
                shutil.copy2(src, dst)
            except Exception as e:
                print(f'[Backup] Warning: could not copy {cfg_name}: {e}')
    print(f'[Backup] Config files backed up alongside DB')

    # Enforce retention limit
    _enforce_retention()

    return backup_filename


def _enforce_retention():
    """Delete oldest backups if count exceeds BACKUP_MAX."""
    backups = _list_backups()
    # Only count regular backups (not pre_restore safety backups) for retention
    regular = [b for b in backups if not b['filename'].startswith('pre_restore_')]
    while len(regular) > BACKUP_MAX:
        oldest = regular.pop()  # list is sorted newest-first, so last = oldest
        try:
            os.remove(os.path.join(BACKUP_DIR, oldest['filename']))
            print(f'[Backup] Retention cleanup: deleted {oldest["filename"]}')
        except OSError as e:
            print(f'[Backup] Error deleting {oldest["filename"]}: {e}')


def _list_backups():
    """Return a list of backup file info dicts, sorted newest first."""
    backups = []
    if not os.path.isdir(BACKUP_DIR):
        return backups
    for fname in os.listdir(BACKUP_DIR):
        if fname.endswith('.db'):
            fpath = os.path.join(BACKUP_DIR, fname)
            stat = os.stat(fpath)
            backups.append({
                'filename': fname,
                'size_bytes': stat.st_size,
                'size_mb': round(stat.st_size / 1024 / 1024, 1),
                'created_at': datetime.datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                'is_safety': fname.startswith('pre_restore_'),
            })
    backups.sort(key=lambda b: b['created_at'], reverse=True)
    return backups


# ── Auto-Backup Scheduler ────────────────────────────────────────────────────

def _auto_backup_check():
    """Background timer callback: create a daily backup if none exists for today."""
    global _backup_timer
    if not _auto_backup_enabled:
        _backup_timer = threading.Timer(_BACKUP_CHECK_INTERVAL, _auto_backup_check)
        _backup_timer.daemon = True
        _backup_timer.start()
        return

    today_prefix = datetime.datetime.now().strftime('inventory_%Y-%m-%d')
    existing = [f for f in os.listdir(BACKUP_DIR) if f.startswith(today_prefix) and f.endswith('.db')]

    if not existing:
        try:
            _create_backup()
            print('[Backup] Auto-daily backup completed.')
        except Exception as e:
            print(f'[Backup] Auto-backup error: {e}')
    else:
        print(f'[Backup] Auto-backup skipped — today\'s backup already exists ({existing[0]})')

    # Schedule next check
    _backup_timer = threading.Timer(_BACKUP_CHECK_INTERVAL, _auto_backup_check)
    _backup_timer.daemon = True
    _backup_timer.start()


def _start_auto_backup_scheduler():
    """Start the auto-backup scheduler in the background."""
    global _backup_timer
    if _backup_timer is not None:
        return  # Already running
    # Run the first check after a short delay (30s after server start)
    _backup_timer = threading.Timer(30, _auto_backup_check)
    _backup_timer.daemon = True
    _backup_timer.start()
    print('[Backup] Auto-backup scheduler started (checks every hour)')


def _update_auto_backup_config(enabled):
    """Update the auto_backup setting in config.ini."""
    cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini')
    cfg = _configparser.ConfigParser()
    cfg.read(cfg_path)
    if not cfg.has_section('backup'):
        cfg.add_section('backup')
    cfg.set('backup', 'auto_backup', 'yes' if enabled else 'no')
    with open(cfg_path, 'w') as f:
        cfg.write(f)


# ── Backup API Endpoints ─────────────────────────────────────────────────────

@app.route('/api/admin/backup', methods=['POST'])
@admin_required
def admin_create_backup():
    """Create a manual backup of the database."""
    try:
        filename = _create_backup()
        _log_audit(session['user'], f'backup_create:{filename}', request.remote_addr)
        return jsonify({'success': True, 'filename': filename})
    except Exception as e:
        print(f'[Backup] Error creating backup: {e}')
        return jsonify({'error': f'Backup failed: {str(e)}'}), 500


@app.route('/api/admin/backups', methods=['GET'])
@admin_required
def admin_list_backups():
    """List all available backups."""
    backups = _list_backups()
    return jsonify({
        'backups': backups,
        'auto_backup': _auto_backup_enabled,
        'max_backups': BACKUP_MAX,
    })


@app.route('/api/admin/backup/restore', methods=['POST'])
@admin_required
def admin_restore_backup():
    """Restore the database from a backup file."""
    data = request.get_json(force=True)
    filename = data.get('filename', '').strip()

    if not filename or not filename.endswith('.db'):
        return jsonify({'error': 'Invalid backup filename'}), 400

    # Sanitize: prevent path traversal
    filename = os.path.basename(filename)
    backup_path = os.path.join(BACKUP_DIR, filename)

    if not os.path.isfile(backup_path):
        return jsonify({'error': 'Backup file not found'}), 404

    try:
        # 1. Create a safety backup of the current DB before restoring
        safety_name = _create_backup(prefix='pre_restore')

        # 2. Restore: copy the backup over the live database
        shutil.copy2(backup_path, DB_FILE)

        _log_audit(session['user'], f'backup_restore:{filename}', request.remote_addr)
        print(f'[Backup] Restored from {filename} (safety backup: {safety_name})')

        return jsonify({
            'success': True,
            'restored_from': filename,
            'safety_backup': safety_name,
            'message': 'Database restored. Please refresh the page to see updated data.'
        })
    except Exception as e:
        print(f'[Backup] Restore error: {e}')
        return jsonify({'error': f'Restore failed: {str(e)}'}), 500


@app.route('/api/admin/backup/<filename>', methods=['DELETE'])
@admin_required
def admin_delete_backup(filename):
    """Delete a specific backup file."""
    filename = os.path.basename(filename)
    backup_path = os.path.join(BACKUP_DIR, filename)

    if not os.path.isfile(backup_path):
        return jsonify({'error': 'Backup file not found'}), 404

    try:
        os.remove(backup_path)
        _log_audit(session['user'], f'backup_delete:{filename}', request.remote_addr)
        print(f'[Backup] Deleted: {filename}')
        return jsonify({'success': True})
    except Exception as e:
        print(f'[Backup] Delete error: {e}')
        return jsonify({'error': f'Delete failed: {str(e)}'}), 500


@app.route('/api/admin/backup/download/<filename>')
@admin_required
def admin_download_backup(filename):
    """Download a specific backup file."""
    filename = os.path.basename(filename)
    backup_path = os.path.join(BACKUP_DIR, filename)

    if not os.path.isfile(backup_path):
        return jsonify({'error': 'Backup file not found'}), 404

    _log_audit(session['user'], f'backup_download:{filename}', request.remote_addr)
    return send_from_directory(BACKUP_DIR, filename, as_attachment=True)


@app.route('/api/admin/backup/schedule', methods=['GET', 'POST'])
@admin_required
def admin_backup_schedule():
    """Get or update the auto-backup schedule setting."""
    global _auto_backup_enabled

    if request.method == 'GET':
        return jsonify({'auto_backup': _auto_backup_enabled})

    data = request.get_json(force=True)
    enabled = bool(data.get('auto_backup', False))
    _auto_backup_enabled = enabled
    _update_auto_backup_config(enabled)
    _log_audit(session['user'], f'backup_schedule:{"on" if enabled else "off"}', request.remote_addr)
    print(f'[Backup] Auto-backup {"enabled" if enabled else "disabled"} by {session["user"]}')
    return jsonify({'success': True, 'auto_backup': enabled})


# ── Global Auth Guard ─────────────────────────────────────────────────────────
# Instead of decorating every route with @login_required, this before_request
# hook checks authentication globally.  Only whitelisted paths are public.

# Paths that can be accessed WITHOUT authentication
_PUBLIC_PATHS = {
    '/',              # Login page (index.html)
    '/api/auth/login',
    '/api/auth/logout',
    '/api/auth/me',
    '/api/logo',
}

# Prefixes that can be accessed without authentication (static assets)
_PUBLIC_PREFIXES = (
    '/index.css',
    '/app.js',
    '/images/',
)

@app.before_request
def check_auth():
    """Reject unauthenticated requests to protected routes."""
    path = request.path
    # Allow public paths
    if path in _PUBLIC_PATHS:
        return None
    # Allow static asset prefixes
    for prefix in _PUBLIC_PREFIXES:
        if path.startswith(prefix):
            return None
    # All other routes require authentication
    if 'user' not in session:
        # For API routes, return JSON 401
        if path.startswith('/api/'):
            return jsonify({'error': 'Authentication required'}), 401
        # For non-API routes (e.g. direct HTML page access), serve index anyway
        # (the JS will handle showing the login overlay)
        return None


# Drop orphaned legacy tables (snapshots & import_log were from ZIND-based workflow,
# no longer used — the webapp now sources all data from CSV extraction scripts).
def _drop_legacy_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    for table in ('snapshots', 'import_log'):
        try:
            cursor.execute(f'DROP TABLE IF EXISTS {table}')
            print(f"[Migration] Dropped legacy table: {table}")
        except Exception:
            pass
    conn.commit()
    conn.close()

_drop_legacy_tables()

# ─── Background Sync System ──────────────────────────────────────────────────
# Monitors Z:\ server files for changes and auto-triggers extraction in the
# background so the webapp always shows fresh data without manual refresh.

# Source file paths to watch on the server
SERVER_SOURCE_FILES = {
    'master': [
        r'Z:\DATA.CTOTAL\CVINDMAS',
        r'Z:\DATA.CTOTAL\CVINDMA1',
        r'Z:\DATA.CTOTAL\CVINDBRA',
    ],
    'ledger': [
        r'Z:\DATA.CTOTAL\CVINDTR1',
        r'Z:\DATA.CTOTAL\CVINDTRN',
        r'Z:\DATA.CTOTAL\CVINDMAS',
    ],
    'customer': [
        r'Z:\DATA.CW\CVARDMAS',
    ],
    'invoice': [
        r'Z:\DATA.CW\CVIVDMAS',
        r'Z:\DATA.CW\CVIVDTRN',
    ],
}

# Background sync state
_sync_lock = threading.Lock()
_cache_lock = threading.RLock()  # Protects global cache reads/writes during background sync
_sync_state = {
    'master':   {'status': 'idle', 'progress': '', 'last_check': None, 'last_sync': None, 'last_size': {}},
    'ledger':   {'status': 'idle', 'progress': '', 'last_check': None, 'last_sync': None, 'last_size': {}},
    'customer': {'status': 'idle', 'progress': '', 'last_check': None, 'last_sync': None, 'last_size': {}},
    'invoice':  {'status': 'idle', 'progress': '', 'last_check': None, 'last_sync': None, 'last_size': {}},
}
_sync_events = []  # list of queue.Queue for SSE subscribers
_file_watcher_thread = None
_file_watcher_running = False

# Stores the changes detected by the most recent sync so that users arriving
# after sync can still see the highlights via /api/sync/changes.
_last_sync_changes = {
    'changed_product_skus': [],   # list of SKU strings
    'new_move_keys': [],          # list of move fingerprint strings
    'detection_times': {},        # sku -> HH:MM string for today's sales
    'disappeared_count': 0,       # number of transactions that vanished from ERP
    'disappeared_transactions': [],  # summary of disappeared entries (capped)
    'timestamp': '',              # when the sync completed
    'source': '',                 # which source triggered these changes
}


def _restore_detection_times():
    """Restore today's detection times from the database on server startup.

    Detection times are persisted to the `csv_last_sold_detected_at` column
    during each sync.  When the server restarts, the in-memory
    `_last_sync_changes` is empty, so the frontend would lose all
    "ตรวจพบเมื่อ HH:MM" tags.  This function reads them back from the DB
    so they survive server restarts.
    """
    today_str = datetime.datetime.now().strftime('%Y-%m-%d')
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT sku, csv_last_sold_detected_at FROM products '
            'WHERE csv_last_sold_detected_at IS NOT NULL '
            'AND csv_last_sold_detected_at LIKE ?',
            (f'{today_str}%',)
        )
        restored = {}
        changed_skus = []
        for row in cursor.fetchall():
            sku = row['sku']
            det_at = row['csv_last_sold_detected_at']  # e.g. "2026-03-14 09:30"
            # Extract the HH:MM portion
            hhmm = det_at[11:16] if len(det_at) >= 16 else det_at[11:]
            if hhmm:
                restored[sku] = hhmm
                changed_skus.append(sku)
        conn.close()

        if restored:
            _last_sync_changes['detection_times'] = restored
            _last_sync_changes['changed_product_skus'] = changed_skus
            _last_sync_changes['timestamp'] = datetime.datetime.now().isoformat()
            _last_sync_changes['source'] = 'startup_restore'
            print(f"[AutoSync] Restored {len(restored)} detection time(s) from DB for today ({today_str})")
        else:
            print(f"[AutoSync] No detection times to restore for today ({today_str})")
    except Exception as e:
        print(f"[AutoSync] Error restoring detection times from DB: {e}")

_restore_detection_times()


# Per-source auto-sync toggle (True = auto-sync enabled, False = manual only)
# Persisted to disk so settings survive server restarts.
SYNC_CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'sync_config.json')

def _load_sync_config():
    """Load toggle states from disk, defaulting to all-OFF."""
    defaults = {'master': False, 'ledger': False, 'customer': False, 'invoice': False}
    if os.path.isfile(SYNC_CONFIG_FILE):
        try:
            with open(SYNC_CONFIG_FILE, 'r') as f:
                saved = json.load(f)
            for key in defaults:
                if key in saved:
                    defaults[key] = bool(saved[key])
            print(f"[AutoSync] Loaded toggle config from {SYNC_CONFIG_FILE}: {defaults}")
        except Exception as e:
            print(f"[AutoSync] Error reading sync config, using defaults: {e}")
    return defaults

def _save_sync_config():
    """Persist current toggle states to disk."""
    try:
        with open(SYNC_CONFIG_FILE, 'w') as f:
            json.dump(_sync_enabled, f)
    except Exception as e:
        print(f"[AutoSync] Error saving sync config: {e}")

_sync_enabled = _load_sync_config()

FILE_CHECK_INTERVAL = 30  # seconds between file change checks


def _broadcast_sync_event(event_type, data):
    """Send an SSE event to all connected clients."""
    msg = json.dumps({'type': event_type, **data})
    dead = []
    for q in _sync_events:
        try:
            q.put_nowait(msg)
        except queue.Full:
            dead.append(q)
    for q in dead:
        try:
            _sync_events.remove(q)
        except ValueError:
            pass


def _get_file_mtimes(source_key):
    """Get modification times for all source files of a given sync type.

    On Windows, SMB/network drives cache directory metadata aggressively.
    os.path.getmtime() can return stale values for minutes on Z:\\ shares.
    To bust the cache, we list the parent directory first (os.listdir),
    which forces Windows to refresh file attributes from the server.
    """
    mtimes = {}
    # Bust the Windows SMB metadata cache by listing parent directories first
    busted_dirs = set()
    for fpath in SERVER_SOURCE_FILES.get(source_key, []):
        parent = os.path.dirname(fpath)
        if parent not in busted_dirs:
            try:
                os.listdir(parent)  # Forces Windows to refresh cached attrs
            except OSError:
                pass
            busted_dirs.add(parent)
    # Now read the actual modification times (freshly fetched)
    for fpath in SERVER_SOURCE_FILES.get(source_key, []):
        try:
            # Use os.stat() directly for the freshest result
            st = os.stat(fpath)
            mtimes[fpath] = st.st_mtime
        except OSError:
            pass
    return mtimes


def _get_file_sizes(source_key):
    """Get file sizes for all source files of a given sync type.

    Uses file size instead of mtime for change detection because ERP software
    frequently 'touches' files (updating mtime) without changing content,
    causing phantom sync triggers.  File size only changes when actual
    records are added or removed — which is what we care about.

    On Windows, SMB/network drives cache directory metadata aggressively.
    os.stat() can return stale values for minutes on Z:\\ shares.
    To bust the cache, we list the parent directory first (os.listdir),
    which forces Windows to refresh file attributes from the server.
    """
    sizes = {}
    # Bust the Windows SMB metadata cache by listing parent directories first
    busted_dirs = set()
    for fpath in SERVER_SOURCE_FILES.get(source_key, []):
        parent = os.path.dirname(fpath)
        if parent not in busted_dirs:
            try:
                os.listdir(parent)  # Forces Windows to refresh cached attrs
            except OSError:
                pass
            busted_dirs.add(parent)
    # Now read the actual file sizes (freshly fetched)
    for fpath in SERVER_SOURCE_FILES.get(source_key, []):
        try:
            st = os.stat(fpath)
            sizes[fpath] = st.st_size
        except OSError:
            pass
    return sizes


def _run_sync_task(source_key):
    """Run extraction for a given source type in the current thread."""
    with _sync_lock:
        if _sync_state[source_key]['status'] == 'syncing':
            return  # Already running
        _sync_state[source_key]['status'] = 'syncing'
        _sync_state[source_key]['progress'] = 'Starting extraction...'

    _broadcast_sync_event('sync_start', {'source': source_key})
    sync_start_time = time.time()

    try:
        script_map = {
            'master': 'extract_product_master.py',
            'ledger': 'extract_stock_ledger_v4.py',
            'customer': 'extract_customer_master.py',
            'invoice': 'extract_invoice.py',
        }
        script_name = script_map.get(source_key)
        if not script_name:
            raise ValueError(f'Unknown source key: {source_key}')

        script_path = os.path.join(os.path.dirname(__file__), 'python script', script_name)
        if not os.path.isfile(script_path):
            raise FileNotFoundError(f'Script not found: {script_path}')

        _sync_state[source_key]['progress'] = f'Running {script_name}...'
        _broadcast_sync_event('sync_progress', {
            'source': source_key,
            'progress': f'Running {script_name}...'
        })

        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True, text=True, timeout=600
        )

        if result.returncode != 0:
            raise RuntimeError(f'Script failed: {result.stderr[:1500]}')

        # Reload caches
        _sync_state[source_key]['progress'] = 'Reloading caches...'
        _broadcast_sync_event('sync_progress', {
            'source': source_key,
            'progress': 'Reloading caches...'
        })

        # ── Snapshot BEFORE reload (for change detection) ────────────
        old_product_dates = {}  # sku -> csv_last_sold_date
        old_today_moves = set()
        old_ledger_keys = set()     # fingerprints of all ledger entries
        old_ledger_details = {}     # key -> full entry dict (for logging)
        today_str = datetime.datetime.now().strftime('%Y-%m-%d')

        if source_key in ('master', 'ledger'):
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT sku, csv_last_sold_date FROM products')
                for row in cursor.fetchall():
                    old_product_dates[row['sku']] = row['csv_last_sold_date'] or ''
                conn.close()
            except Exception:
                pass  # DB may not have the column yet

            # Snapshot today's moves for diff
            for m in all_ledger_moves:
                if m['date'] == today_str:
                    key = f"{m['part_code']}|{m['date']}|{m['doc_ref']}|{m['qty_in']}|{m['qty_out']}"
                    old_today_moves.add(key)

            # Snapshot ALL ledger entries for disappearance detection
            if source_key == 'ledger' and archived_history_cache is not None and len(archived_history_cache) > 0:
                for (part_code, sku_type), entries in archived_history_cache.items():
                    for entry in entries:
                        if entry.get('doc_ref') == 'OPENING':
                            continue  # Skip synthetic opening balances
                        lkey = f"{part_code}|{sku_type}|{entry.get('doc_ref','')}|{entry.get('date','')}"
                        old_ledger_keys.add(lkey)
                        old_ledger_details[lkey] = {
                            'part_code': part_code,
                            'sku_type': sku_type,
                            'doc_ref': entry.get('doc_ref', ''),
                            'date': entry.get('date', ''),
                            'category_name': entry.get('category_name', ''),
                            'from_to': entry.get('from_to', ''),
                            'qty_in': entry.get('qty_in', 0),
                            'qty_out': entry.get('qty_out', 0),
                            'unit_price': entry.get('unit_price', 0),
                        }

        # ── Reload caches ────────────────────────────────────────────
        if source_key == 'master':
            _reload_master_from_csv()
        elif source_key == 'ledger':
            load_archived_history_cache()
        elif source_key == 'customer':
            load_customer_master_cache()
        elif source_key == 'invoice':
            load_invoice_cache()

        # ── Compute diff AFTER reload ────────────────────────────────
        changes = {'changed_product_skus': [], 'new_move_keys': [],
                   'detection_times': {}, 'disappeared_count': 0,
                   'disappeared_transactions': [],
                   'timestamp': '', 'source': source_key}

        if source_key in ('master', 'ledger') and old_product_dates:
            det_time = datetime.datetime.now().strftime('%H:%M')
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT sku, csv_last_sold_date FROM products')
                for row in cursor.fetchall():
                    sku = row['sku']
                    new_date = row['csv_last_sold_date'] or ''
                    old_date = old_product_dates.get(sku)
                    is_new = (old_date is None)
                    date_changed = (not is_new and new_date and new_date != old_date)
                    if is_new or date_changed:
                        changes['changed_product_skus'].append(sku)
                        if new_date == today_str:
                            changes['detection_times'][sku] = det_time
                # Persist detection times to DB for sort tiebreaker
                if changes['detection_times']:
                    for det_sku, det_hhmm in changes['detection_times'].items():
                        det_full = f"{today_str} {det_hhmm}"
                        cursor.execute(
                            'UPDATE products SET csv_last_sold_detected_at = ? WHERE sku = ?',
                            (det_full, det_sku)
                        )
                    conn.commit()
                conn.close()
            except Exception as e:
                print(f'[AutoSync] Error computing product diff: {e}')

            # New moves with today's date
            for m in all_ledger_moves:
                if m['date'] == today_str:
                    key = f"{m['part_code']}|{m['date']}|{m['doc_ref']}|{m['qty_in']}|{m['qty_out']}"
                    if key not in old_today_moves:
                        changes['new_move_keys'].append(key)

            # ── Detect disappeared transactions ──────────────────────
            if source_key == 'ledger' and old_ledger_keys:
                new_ledger_keys = set()
                for (part_code, sku_type), entries in archived_history_cache.items():
                    for entry in entries:
                        if entry.get('doc_ref') == 'OPENING':
                            continue
                        lkey = f"{part_code}|{sku_type}|{entry.get('doc_ref','')}|{entry.get('date','')}"
                        new_ledger_keys.add(lkey)

                disappeared_keys = old_ledger_keys - new_ledger_keys
                if disappeared_keys:
                    _handle_disappeared_transactions(disappeared_keys, old_ledger_details)
                    changes['disappeared_count'] = len(disappeared_keys)
                    # Include summary in SSE payload (cap at 20 for bandwidth)
                    for dk in sorted(disappeared_keys)[:20]:
                        d = old_ledger_details.get(dk, {})
                        changes['disappeared_transactions'].append({
                            'part_code': d.get('part_code', ''),
                            'sku_type': d.get('sku_type', ''),
                            'doc_ref': d.get('doc_ref', ''),
                            'date': d.get('date', ''),
                            'category_name': d.get('category_name', ''),
                            'qty_in': d.get('qty_in', 0),
                            'qty_out': d.get('qty_out', 0),
                        })

            changes['timestamp'] = datetime.datetime.now().isoformat()

            # Merge detection_times with previous sync results (accumulate all
            # detections throughout the day). Clear if the day has rolled over.
            prev_ts = _last_sync_changes.get('timestamp', '')
            prev_day = prev_ts[:10] if prev_ts else ''
            if prev_day == today_str:
                # Same day: keep previous detection times, add new ones
                merged_det = dict(_last_sync_changes.get('detection_times', {}))
                merged_det.update(changes['detection_times'])
                changes['detection_times'] = merged_det
            # else: new day — start fresh (changes already has only today's)

            _last_sync_changes.update(changes)
            n_prod = len(changes['changed_product_skus'])
            n_moves = len(changes['new_move_keys'])
            n_det = len(changes['detection_times'])
            n_disappeared = changes['disappeared_count']
            log_parts = [f'{n_prod} products', f'{n_moves} moves', f'{n_det} today-sales']
            if n_disappeared > 0:
                log_parts.append(f'⚠️  {n_disappeared} DISAPPEARED')
            print(f'[AutoSync] Changes detected: {", ".join(log_parts)}')

        _sync_state[source_key]['status'] = 'done'
        _sync_state[source_key]['progress'] = 'Sync complete'
        _sync_state[source_key]['last_sync'] = datetime.datetime.now().isoformat()
        _sync_state[source_key]['last_size'] = _get_file_sizes(source_key)

        _broadcast_sync_event('sync_done', {'source': source_key, 'changes': changes})
        elapsed = time.time() - sync_start_time
        elapsed_min = int(elapsed // 60)
        elapsed_sec = elapsed % 60
        print(f"[AutoSync] {source_key} sync completed successfully. (Time: {elapsed_min}m {elapsed_sec:.1f}s)")

    except Exception as e:
        _sync_state[source_key]['status'] = 'error'
        _sync_state[source_key]['progress'] = str(e)[:200]
        _broadcast_sync_event('sync_error', {
            'source': source_key,
            'error': str(e)[:200]
        })
        elapsed = time.time() - sync_start_time
        elapsed_min = int(elapsed // 60)
        elapsed_sec = elapsed % 60
        print(f"[AutoSync] {source_key} sync failed: {e} (Time: {elapsed_min}m {elapsed_sec:.1f}s)")

    # Reset to idle after a brief delay so the UI can show the result
    def _reset_to_idle():
        time.sleep(5)
        _sync_state[source_key]['status'] = 'idle'
        _sync_state[source_key]['progress'] = ''
    threading.Thread(target=_reset_to_idle, daemon=True).start()


def _handle_disappeared_transactions(disappeared_keys, old_details):
    """Log transactions that existed in previous sync but vanished from ERP.

    Writes to a persistent JSON log file so the audit trail survives restarts.
    Groups alerts: only details recent transactions (last 365 days) individually;
    older ones are summarized by year.
    """
    log_path = os.path.join(ARCHIVED_LEDGER_DIR, 'disappeared_transactions.json')

    # Load existing log
    existing = []
    if os.path.isfile(log_path):
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        except Exception:
            existing = []

    timestamp = datetime.datetime.now().isoformat()
    one_year_ago = (datetime.datetime.now() - datetime.timedelta(days=365)).strftime('%Y-%m-%d')

    recent = []   # transactions within last 365 days (detailed)
    older = {}    # year -> count (summarized)

    for key in sorted(disappeared_keys):
        detail = old_details.get(key, {})
        txn_date = detail.get('date', '')
        entry = {
            'key': key,
            'part_code': detail.get('part_code', ''),
            'sku_type': detail.get('sku_type', ''),
            'doc_ref': detail.get('doc_ref', ''),
            'date': txn_date,
            'category_name': detail.get('category_name', ''),
            'from_to': detail.get('from_to', ''),
            'qty_in': detail.get('qty_in', 0),
            'qty_out': detail.get('qty_out', 0),
            'unit_price': detail.get('unit_price', 0),
        }
        if txn_date >= one_year_ago:
            recent.append(entry)
        else:
            yr = txn_date[:4] if txn_date else 'unknown'
            older[yr] = older.get(yr, 0) + 1

    batch = {
        'detected_at': timestamp,
        'total_count': len(disappeared_keys),
        'recent_count': len(recent),
        'older_summary': older,
        'transactions': recent,
    }

    existing.append(batch)

    # Keep last 100 batches to avoid unbounded growth
    try:
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(existing[-100:], f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[AutoSync] Error writing disappeared transactions log: {e}")

    # Console alert
    print(f"[AutoSync] ⚠️  DISAPPEARED: {len(disappeared_keys)} transaction(s) "
          f"missing from ERP! ({len(recent)} recent, {sum(older.values())} older)")
    print(f"[AutoSync]    Logged to {log_path}")
    if recent:
        for t in recent[:5]:
            print(f"[AutoSync]    - {t['date']} {t['doc_ref']} {t['part_code']} "
                  f"in={t['qty_in']} out={t['qty_out']}")
        if len(recent) > 5:
            print(f"[AutoSync]    ... and {len(recent) - 5} more recent")


def _reload_master_from_csv():
    """Reload product master from CSV into the database (shared logic)."""
    csv_path = os.path.join(os.path.dirname(__file__), 'product master table', 'product_master_active.csv')
    if not os.path.isfile(csv_path):
        print("product_master_active.csv not found after extraction")
        return

    products = []
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            products.append(row)

    if not products:
        print("No products found in CSV")
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM products')

    def safe_float(val):
        try:
            return float(str(val).replace(',', '')) if val else 0.0
        except (ValueError, TypeError):
            return 0.0

    count = 0
    for p in products:
        sku_code = p.get('sku', '').strip()
        suffix = p.get('type', '').strip()
        if not sku_code or not suffix:
            continue
        sku = f"{sku_code}_{suffix}"
        image_lookup_part = sku_code
        if image_lookup_part.endswith('R'):
            image_lookup_part = image_lookup_part[:-1]
        thumbnail, image_count = find_thumbnail(image_lookup_part)
        if not thumbnail and image_lookup_part != sku_code:
            thumbnail, image_count = find_thumbnail(sku_code)
        qty = safe_float(p.get('qty_on_hand', 0))
        sale_price = safe_float(p.get('selling_price', 0))
        unit_cost = safe_float(p.get('unit_cost', 0))
        market_price = safe_float(p.get('market_price', 0))
        cursor.execute('''
            INSERT OR REPLACE INTO products (
                sku, part_code, suffix, suffix_label, name_eng, name_thai, size, brand,
                qty, sale_price, unit_cost, market_price, thumbnail, image_count, locations
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            sku, sku_code, suffix, SUFFIX_MAP.get(suffix, 'Unknown'),
            p.get('name_en', ''), p.get('name_th', ''),
            p.get('specification', ''), p.get('brand', ''),
            int(qty), sale_price, unit_cost, market_price,
            thumbnail or '', image_count, p.get('warehouse', '')
        ))
        count += 1
    conn.commit()
    conn.close()

    # Re-sync cached ledger data (qty, last_sold_date) to the updated products table.
    # No need to re-read the ledger CSV — only the product table changed.
    _sync_csv_data_to_db()
    _build_moves_list()
    print(f"Product master refreshed: {count} active products loaded from CSV.")



# Map each source to its primary local output file (used for startup staleness check)
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_LOCAL_OUTPUT_FILES = {
    'master':   os.path.join(_BASE_DIR, 'product master table', 'product_master_active.csv'),
    'ledger':   os.path.join(_BASE_DIR, 'ledger', 'stock_ledger_full.csv'),
    'customer': os.path.join(_BASE_DIR, 'customer master table', 'customer_master.csv'),
    'invoice':  os.path.join(_BASE_DIR, 'invoice', 'invoice_headers.csv'),
}


def _check_startup_staleness():
    """Compare Z: source file timestamps against local output CSVs.
    If any source's Z: files are newer than the local output, trigger sync.
    This ensures the mini PC gets fresh data immediately after a fresh deploy."""
    stale_sources = []
    for source_key, local_csv in _LOCAL_OUTPUT_FILES.items():
        if not _sync_enabled.get(source_key, False):
            continue  # Skip sources with auto-sync disabled

        # Get the newest Z: source file mtime
        source_mtimes = _get_file_mtimes(source_key)
        if not source_mtimes:
            continue  # Can't reach Z: drive
        newest_source = max(source_mtimes.values())

        # Get local output CSV mtime
        local_mtime = 0
        # Also check .new variant for ledger
        for path in [local_csv, local_csv + '.new']:
            try:
                local_mtime = max(local_mtime, os.path.getmtime(path))
            except OSError:
                pass

        if local_mtime == 0:
            # Local CSV doesn't exist — definitely stale
            stale_sources.append((source_key, 'missing'))
        elif newest_source > local_mtime:
            # Z: drive has newer data
            age_mins = (newest_source - local_mtime) / 60
            stale_sources.append((source_key, f'{age_mins:.0f}min behind'))

    if stale_sources:
        names = ', '.join(f'{k} ({reason})' for k, reason in stale_sources)
        print(f"[AutoSync] Startup staleness detected: {names}")
        for source_key, reason in stale_sources:
            if _sync_state[source_key]['status'] == 'idle':
                print(f"[AutoSync] Triggering startup sync for: {source_key} ({reason})")
                t = threading.Thread(target=_run_sync_task, args=(source_key,), daemon=True)
                t.start()
                time.sleep(1)  # Stagger launches slightly
    else:
        print("[AutoSync] All local data is up to date — no startup sync needed.")


def _file_watcher_loop():
    r"""Background thread that checks Z:\ source files for changes."""
    global _file_watcher_running
    print("[AutoSync] File watcher started. Checking every", FILE_CHECK_INTERVAL, "seconds.")

    # Initialize mtimes on first run
    for key in SERVER_SOURCE_FILES:
        _sync_state[key]['last_size'] = _get_file_sizes(key)
        _sync_state[key]['last_check'] = datetime.datetime.now().isoformat()

    # Check if local output CSVs are stale compared to Z: source files
    _check_startup_staleness()

    while _file_watcher_running:
        time.sleep(FILE_CHECK_INTERVAL)
        if not _file_watcher_running:
            break

        for source_key in SERVER_SOURCE_FILES:
            try:
                current_sizes = _get_file_sizes(source_key)
                old_sizes = _sync_state[source_key].get('last_size', {})
                _sync_state[source_key]['last_check'] = datetime.datetime.now().isoformat()

                # Check if any file's size has changed (ignores mtime-only touches)
                changed = False
                if not old_sizes and current_sizes:
                    changed = True  # First time seeing files
                else:
                    for fpath, size in current_sizes.items():
                        if fpath not in old_sizes or old_sizes[fpath] != size:
                            changed = True
                            old_sz = old_sizes.get(fpath, '?')
                            print(f"[AutoSync] Size changed in {os.path.basename(fpath)} for {source_key}: {old_sz} -> {size}")
                            break

                if changed and _sync_state[source_key]['status'] == 'idle':
                    if not _sync_enabled.get(source_key, False):
                        # Auto-sync disabled for this source — update sizes silently
                        _sync_state[source_key]['last_size'] = current_sizes
                        continue
                    print(f"[AutoSync] Triggering background sync for: {source_key}")
                    t = threading.Thread(target=_run_sync_task, args=(source_key,), daemon=True)
                    t.start()

            except Exception as e:
                print(f"[AutoSync] Error checking {source_key}: {e}")

    print("[AutoSync] File watcher stopped.")


def start_file_watcher():
    """Start the background file watcher thread."""
    global _file_watcher_thread, _file_watcher_running
    if _file_watcher_thread and _file_watcher_thread.is_alive():
        return
    _file_watcher_running = True
    _file_watcher_thread = threading.Thread(target=_file_watcher_loop, daemon=True)
    _file_watcher_thread.start()


# ─── SSE endpoint for real-time sync status ──────────────────────────────────

@app.route('/api/sync/events')
def sync_events_stream():
    """Server-Sent Events endpoint for real-time sync status updates."""
    def generate():
        q = queue.Queue(maxsize=100)
        _sync_events.append(q)
        try:
            # Send current state immediately
            with _sync_lock:
                state_snapshot = {k: {'status': v['status'], 'progress': v['progress'],
                                      'last_sync': v['last_sync'], 'last_check': v['last_check']}
                                  for k, v in _sync_state.items()}
            yield f"data: {json.dumps({'type': 'init', 'state': state_snapshot, 'enabled': dict(_sync_enabled)})}\n\n"

            while True:
                try:
                    msg = q.get(timeout=30)  # 30s heartbeat
                    yield f"data: {msg}\n\n"
                except queue.Empty:
                    yield f": heartbeat\n\n"  # Keep connection alive
        except GeneratorExit:
            pass
        finally:
            try:
                _sync_events.remove(q)
            except ValueError:
                pass

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        }
    )


@app.route('/api/sync/status')
def sync_status():
    """Return current sync status for all sources."""
    with _sync_lock:
        return jsonify({k: {'status': v['status'], 'progress': v['progress'],
                            'last_sync': v['last_sync'], 'last_check': v['last_check']}
                        for k, v in _sync_state.items()})


@app.route('/api/sync/config', methods=['GET'])
def get_sync_config():
    """Return current auto-sync enabled/disabled state for each source."""
    return jsonify(_sync_enabled)


@app.route('/api/sync/config', methods=['POST'])
def set_sync_config():
    """Update auto-sync enabled/disabled state per source."""
    data = request.get_json(force=True)
    changed = []
    for key in _sync_enabled:
        if key in data:
            new_val = bool(data[key])
            if _sync_enabled[key] != new_val:
                _sync_enabled[key] = new_val
                changed.append(key)
                state_str = 'ON' if new_val else 'OFF'
                print(f"[AutoSync] {key} auto-sync turned {state_str}")
    # Broadcast config change to all SSE clients
    if changed:
        _save_sync_config()
    _broadcast_sync_event('config_update', {'enabled': dict(_sync_enabled)})
    return jsonify({'success': True, 'enabled': dict(_sync_enabled), 'changed': changed})


@app.route('/api/sync/trigger/<source_key>', methods=['POST'])
def trigger_sync(source_key):
    """Manually trigger a background sync for a specific source (always works, ignores toggle)."""
    if source_key not in SERVER_SOURCE_FILES:
        return jsonify({'success': False, 'message': f'Unknown source: {source_key}'}), 400

    if _sync_state[source_key]['status'] == 'syncing':
        return jsonify({'success': False, 'message': f'{source_key} is already syncing'})

    t = threading.Thread(target=_run_sync_task, args=(source_key,), daemon=True)
    t.start()
    return jsonify({'success': True, 'message': f'{source_key} sync started in background'})


@app.route('/api/sync/changes')
def get_sync_changes():
    """Return the changes detected by the most recent sync.
    Used by new page loads to show highlights for users arriving after sync."""
    return jsonify(_last_sync_changes)


@app.route('/api/disappeared-transactions')
def get_disappeared_transactions():
    """Return the audit log of transactions that disappeared from the ERP."""
    log_path = os.path.join(ARCHIVED_LEDGER_DIR, 'disappeared_transactions.json')
    if not os.path.isfile(log_path):
        return jsonify([])
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/logo')
def serve_logo():
    if os.path.isfile(LOGO_FILE):
        return send_from_directory(os.path.dirname(LOGO_FILE), os.path.basename(LOGO_FILE))
    return "Logo not found", 404

@app.route('/images/<path:filename>')
def serve_image(filename):
    """Serve an image file, searching primary directory first then secondary.
    Blocks access to files with the _hidden_ prefix."""
    basename = os.path.basename(filename)
    if basename.startswith('_hidden_'):
        return 'Not found', 404
    for img_dir in IMAGE_DIRS:
        full_path = os.path.join(img_dir, filename)
        if os.path.isfile(full_path):
            return send_from_directory(img_dir, filename)
    # Fallback to primary dir (will return 404 naturally)
    return send_from_directory(IMAGE_DIRS[0] if IMAGE_DIRS else '.', filename)

@app.route('/api/stats')
def get_stats():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) as total_skus, SUM(qty) as total_qty FROM products')
    row = cursor.fetchone()

    cursor.execute('SELECT COUNT(DISTINCT brand) as total_brands FROM products WHERE brand != ""')
    brand_row = cursor.fetchone()

    conn.close()

    ledger_mod_date = '-'
    csv_file_path = os.path.join(ARCHIVED_LEDGER_DIR, 'stock_ledger_full.csv')
    csv_new_path = csv_file_path + '.new'
    # Check both original and .new file, use the newest timestamp
    ledger_mtime = 0
    if os.path.exists(csv_file_path):
        ledger_mtime = os.path.getmtime(csv_file_path)
    if os.path.exists(csv_new_path):
        ledger_mtime = max(ledger_mtime, os.path.getmtime(csv_new_path))
    if ledger_mtime > 0:
        ledger_mod_date = datetime.datetime.fromtimestamp(ledger_mtime).strftime('%d/%m/%Y %H:%M:%S')

    master_mod_date = '-'
    master_csv_path = os.path.join(os.path.dirname(__file__), 'product master table', 'product_master_active.csv')
    if os.path.exists(master_csv_path):
        mtime = os.path.getmtime(master_csv_path)
        master_mod_date = datetime.datetime.fromtimestamp(mtime).strftime('%d/%m/%Y %H:%M:%S')

    invoice_mod_date = '-'
    invoice_headers_csv = os.path.join(INVOICE_DIR, 'invoice_headers.csv')
    if os.path.exists(invoice_headers_csv):
        mtime = os.path.getmtime(invoice_headers_csv)
        invoice_mod_date = datetime.datetime.fromtimestamp(mtime).strftime('%d/%m/%Y %H:%M:%S')

    customer_mod_date = '-'
    if os.path.exists(CUSTOMER_MASTER_CSV):
        mtime = os.path.getmtime(CUSTOMER_MASTER_CSV)
        customer_mod_date = datetime.datetime.fromtimestamp(mtime).strftime('%d/%m/%Y %H:%M:%S')

    return jsonify({
        'total_skus': row['total_skus'],
        'total_qty': row['total_qty'],
        'total_brands': brand_row['total_brands'],
        'ledger_mod_date': ledger_mod_date,
        'master_mod_date': master_mod_date,
        'invoice_mod_date': invoice_mod_date,
        'customer_mod_date': customer_mod_date
    })

@app.route('/api/brands')
def get_brands():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT brand FROM products WHERE brand != "" ORDER BY brand')
    brands = [row['brand'] for row in cursor.fetchall()]
    conn.close()
    return jsonify(brands)

@app.route('/api/suffixes')
def get_suffixes():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT suffix, suffix_label FROM products ORDER BY suffix')
    suffixes = [{'id': row['suffix'], 'label': row['suffix_label']} for row in cursor.fetchall()]
    conn.close()
    return jsonify(suffixes)

@app.route('/api/products')
def get_products():
    conn = None
    try:
        search = request.args.get('search', '').strip()
        brand = request.args.get('brand', '')
        suffix = request.args.get('suffix', '')
        active_days = request.args.get('active_days', '')
        sort_by = request.args.get('sort', 'last_sold_date')
        sort_dir = request.args.get('dir', 'desc').lower()
        page = int(request.args.get('page', 1))
        per_page = max(1, int(request.args.get('per_page', 50)))

        valid_sorts = ['part_code', 'name_eng', 'name_thai', 'brand', 'qty', 'sale_price', 'suffix', 'size', 'locations', 'last_sold_date', 'amount_sold', 'relevance']
        if sort_by not in valid_sorts:
            sort_by = 'last_sold_date'
        if sort_dir not in ['asc', 'desc']:
            sort_dir = 'asc'

        query_select_from = "SELECT * FROM products p"
        count_select_from = "SELECT COUNT(*) FROM products p"
        where_clause = " WHERE 1=1"
        params = []

        if search:
            search_term = f"%{search}%"
            where_clause += " AND (p.part_code LIKE ? OR p.name_eng LIKE ? OR p.name_thai LIKE ? OR p.sku LIKE ?)"
            params.extend([search_term, search_term, search_term, search_term])

        if brand:
            where_clause += " AND p.brand = ?"
            params.append(brand)

        if suffix:
            where_clause += " AND p.suffix = ?"
            params.append(suffix)

        if active_days and active_days.isdigit():
            days = int(active_days)
            threshold_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime('%Y-%m-%d')
            
            # Filter products that had sales within the threshold using CSV-sourced last_sold_date
            query_select_from = """
                SELECT p.*, p.csv_last_sold_date as last_sold_date,
                       f.flag_type, f.note as flag_note, f.flagged_at, f.flagged_by
                FROM products p
                LEFT JOIN stock_flags f ON p.sku = f.sku
            """
            where_clause += " AND p.csv_last_sold_date IS NOT NULL AND p.csv_last_sold_date >= ?"
            params.append(threshold_date)
            
            count_select_from = "SELECT COUNT(*) FROM products p"
            
            count_params = list(params)
            query_params = list(params)

        else:
            # Default view: use CSV-sourced last_sold_date directly from products table
            query_select_from = """
                SELECT p.*, p.csv_last_sold_date as last_sold_date,
                       f.flag_type, f.note as flag_note, f.flagged_at, f.flagged_by
                FROM products p
                LEFT JOIN stock_flags f ON p.sku = f.sku
            """
            count_select_from = "SELECT COUNT(*) FROM products p"
            
            count_params = list(params)
            query_params = list(params)

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # In both cases count_select_from joined on p handles count
        cursor.execute(count_select_from + where_clause, count_params)
        total_items = cursor.fetchone()[0]

        # Build ORDER BY clause
        if sort_by == 'relevance' and search:
            # Relevance scoring: exact > starts-with > contains in part_code > name matches
            order_clause = """ ORDER BY
                CASE
                    WHEN p.part_code = ? THEN 0
                    WHEN p.sku = ? THEN 1
                    WHEN p.part_code LIKE ? THEN 2
                    WHEN p.part_code LIKE ? THEN 3
                    WHEN p.name_eng LIKE ? THEN 4
                    WHEN p.name_thai LIKE ? THEN 5
                    ELSE 6
                END ASC, p.part_code ASC
                LIMIT ? OFFSET ?
            """
            starts_with = f"{search}%"
            contains = f"%{search}%"
            query_params.extend([search, search, starts_with, contains, contains, contains, per_page, (page - 1) * per_page])
        else:
            if sort_by == 'relevance':
                # Fallback when no search term: just use last_sold_date
                sort_by = 'last_sold_date'
            # When sorting by last_sold_date, use detection time as tiebreaker
            # so items detected more recently appear first among same-date items
            if sort_by == 'last_sold_date':
                order_clause = f" ORDER BY last_sold_date {sort_dir}, p.csv_last_sold_detected_at {sort_dir} LIMIT ? OFFSET ?"
            else:
                order_clause = f" ORDER BY {sort_by} {sort_dir} LIMIT ? OFFSET ?"
            query_params.extend([per_page, (page - 1) * per_page])

        query = query_select_from + where_clause + order_clause

        cursor.execute(query, query_params)
        products = [dict(row) for row in cursor.fetchall()]

        # Inject on_hand_qty from archived ledger CSV (csv_last_sold_date is already in DB)
        global archived_history_cache
        if archived_history_cache is None:
            load_archived_history_cache()

        # Snapshot cache refs under lock for thread safety during background sync
        with _cache_lock:
            _qty_snap = archived_qty_cache
            _hist_snap = archived_history_cache

        # Compute days_ago on the server so clients with wrong PC clocks still get correct values
        server_today = datetime.date.today()
        server_today_str = server_today.strftime('%Y-%m-%d')

        for p in products:
            key = (p.get('part_code', ''), p.get('suffix', ''))
            p['on_hand_qty'] = _qty_snap.get(key, p['qty'])

            # Compute amount_sold from CSV cache when Activity filter is active
            if active_days and active_days.isdigit():
                entries = _hist_snap.get(key, [])
                total_out = sum(e['qty_out'] for e in entries if e['date'] >= threshold_date)
                p['amount_sold'] = total_out

            # Compute days_ago from last_sold_date (server-side, avoids client clock issues)
            sold_date_str = p.get('last_sold_date') or p.get('csv_last_sold_date')
            if sold_date_str:
                try:
                    sold_date = datetime.date.fromisoformat(sold_date_str)
                    p['days_ago'] = (server_today - sold_date).days  # negative = future
                except (ValueError, TypeError):
                    p['days_ago'] = None
            else:
                p['days_ago'] = None

        return jsonify({
            'items': products,
            'total': total_items,
            'page': page,
            'per_page': per_page,
            'total_pages': math.ceil(total_items / per_page),
            'server_today': server_today_str
        })
    finally:
        if conn:
            conn.close()

@app.route('/api/products/<sku>/detail')
def get_product_detail(sku):
    """Return a single product's full data by SKU. Used when the page is refreshed
    while a product modal is open and the product data isn't available in the frontend state."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.*, p.csv_last_sold_date as last_sold_date,
                   f.flag_type, f.note as flag_note, f.flagged_at, f.flagged_by
            FROM products p
            LEFT JOIN stock_flags f ON p.sku = f.sku
            WHERE p.sku = ?
        ''', (sku,))
        row = cursor.fetchone()
    finally:
        conn.close()

    if not row:
        return jsonify({'error': 'Product not found'}), 404

    product = dict(row)

    # Inject on_hand_qty from archived ledger cache
    global archived_history_cache
    if archived_history_cache is None:
        load_archived_history_cache()

    with _cache_lock:
        _qty_snap = archived_qty_cache

    key = (product.get('part_code', ''), product.get('suffix', ''))
    product['on_hand_qty'] = _qty_snap.get(key, product['qty'])

    # Compute days_ago server-side
    server_today = datetime.date.today()
    sold_date_str = product.get('last_sold_date') or product.get('csv_last_sold_date')
    if sold_date_str:
        try:
            sold_date = datetime.date.fromisoformat(sold_date_str)
            product['days_ago'] = (server_today - sold_date).days
        except (ValueError, TypeError):
            product['days_ago'] = None
    else:
        product['days_ago'] = None

    return jsonify(product)


@app.route('/api/products/<sku>/images')
def get_product_images(sku):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT part_code FROM products WHERE sku = ?', (sku,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({'error': 'Product not found'}), 404

    part_code = row['part_code']
    lookup_code = part_code[:-1] if part_code.endswith('R') else part_code

    images = []

    # Helper: find images in a single directory with optional first-token matching
    def _find_images_in_dir(img_dir, folder_map, use_first_token, code):
        if not img_dir:
            return None
        if use_first_token:
            full_folder = folder_map.get(code)
            if full_folder:
                part_dir = os.path.join(img_dir, full_folder)
                files = [f for f in os.listdir(part_dir)
                         if os.path.isfile(os.path.join(part_dir, f)) and not f.startswith('_hidden_')]
                if files:
                    files.sort()
                    return [f"/images/{full_folder}/{f}" for f in files]
        else:
            part_dir = os.path.join(img_dir, code)
            if os.path.isdir(part_dir):
                files = [f for f in os.listdir(part_dir)
                         if os.path.isfile(os.path.join(part_dir, f)) and not f.startswith('_hidden_')]
                if files:
                    files.sort()
                    return [f"/images/{code}/{f}" for f in files]
        return None

    # Search for images across configured directories
    for code in [lookup_code, part_code] if lookup_code != part_code else [lookup_code]:
        # 1. Try primary directory
        result = _find_images_in_dir(IMAGE_DIR_PRIMARY, _primary_folder_map, PRIMARY_MATCH_FIRST_TOKEN, code)
        if result:
            return jsonify(result)

        # 2. Try secondary directory
        result = _find_images_in_dir(IMAGE_DIR_SECONDARY, _secondary_folder_map, SECONDARY_MATCH_FIRST_TOKEN, code)
        if result:
            return jsonify(result)

    return jsonify(images)


def _resolve_image_dir(sku):
    """Resolve the image folder path and relative prefix for a product SKU.
    Returns list of (abs_dir_path, relative_folder_name) tuples."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT part_code FROM products WHERE sku = ?', (sku,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return []

    part_code = row['part_code']
    lookup_code = part_code[:-1] if part_code.endswith('R') else part_code
    results = []

    for code in ([lookup_code, part_code] if lookup_code != part_code else [lookup_code]):
        # Primary directory
        if IMAGE_DIR_PRIMARY:
            if PRIMARY_MATCH_FIRST_TOKEN:
                full_folder = _primary_folder_map.get(code)
                if full_folder:
                    d = os.path.join(IMAGE_DIR_PRIMARY, full_folder)
                    if os.path.isdir(d):
                        results.append((d, full_folder))
            else:
                d = os.path.join(IMAGE_DIR_PRIMARY, code)
                if os.path.isdir(d):
                    results.append((d, code))
        # Secondary directory
        if IMAGE_DIR_SECONDARY:
            if SECONDARY_MATCH_FIRST_TOKEN:
                full_folder = _secondary_folder_map.get(code)
                if full_folder:
                    d = os.path.join(IMAGE_DIR_SECONDARY, full_folder)
                    if os.path.isdir(d):
                        results.append((d, full_folder))
            else:
                d = os.path.join(IMAGE_DIR_SECONDARY, code)
                if os.path.isdir(d):
                    results.append((d, code))
    return results


@app.route('/api/products/<sku>/images/hide', methods=['POST'])
def hide_product_image(sku):
    """Rename an image file with _hidden_ prefix to remove it from the gallery."""
    data = request.get_json(force=True)
    filename = data.get('filename', '').strip()
    if not filename or '/' in filename or '\\' in filename or filename.startswith('_hidden_'):
        return jsonify({'success': False, 'message': 'Invalid filename'}), 400

    dirs = _resolve_image_dir(sku)
    for abs_dir, rel_folder in dirs:
        src = os.path.join(abs_dir, filename)
        if os.path.isfile(src):
            dst = os.path.join(abs_dir, f'_hidden_{filename}')
            try:
                os.rename(src, dst)
                print(f"[ImageHide] Hidden: {src} -> {dst}")
                return jsonify({'success': True, 'message': f'{filename} hidden'})
            except OSError as e:
                return jsonify({'success': False, 'message': str(e)}), 500

    return jsonify({'success': False, 'message': 'File not found'}), 404


@app.route('/api/products/<sku>/images/unhide', methods=['POST'])
def unhide_product_image(sku):
    """Remove the _hidden_ prefix from a previously hidden image."""
    data = request.get_json(force=True)
    filename = data.get('filename', '').strip()
    if not filename or not filename.startswith('_hidden_'):
        return jsonify({'success': False, 'message': 'Invalid filename'}), 400

    original_name = filename[len('_hidden_'):]
    dirs = _resolve_image_dir(sku)
    for abs_dir, rel_folder in dirs:
        src = os.path.join(abs_dir, filename)
        if os.path.isfile(src):
            dst = os.path.join(abs_dir, original_name)
            try:
                os.rename(src, dst)
                print(f"[ImageHide] Restored: {src} -> {dst}")
                return jsonify({'success': True, 'message': f'{original_name} restored'})
            except OSError as e:
                return jsonify({'success': False, 'message': str(e)}), 500

    return jsonify({'success': False, 'message': 'File not found'}), 404


@app.route('/api/products/<sku>/images/hidden')
def get_hidden_product_images(sku):
    """List only the hidden images for a product (files with _hidden_ prefix)."""
    dirs = _resolve_image_dir(sku)
    for abs_dir, rel_folder in dirs:
        files = [f for f in os.listdir(abs_dir)
                 if os.path.isfile(os.path.join(abs_dir, f)) and f.startswith('_hidden_')]
        if files:
            files.sort()
            return jsonify([{'hidden_name': f, 'original_name': f[len('_hidden_'):],
                             'preview': f'/images/{rel_folder}/{f[len("_hidden_"):]}'} for f in files])
    return jsonify([])


# --- Archived History Cache ---
archived_history_cache = None
archived_qty_cache = {}   # (sku, sku_type) -> last running_balance from CSV
archived_last_sale_cache = {}  # (sku, sku_type) -> last date with qty_out > 0
customer_activity_cache = defaultdict(list)

# --- Customer Master Cache ---
customer_master_cache = {}  # customer_code -> dict of master fields

CUSTOMER_MASTER_CSV = os.path.join(os.path.dirname(__file__), 'customer master table', 'customer_master.csv')

def load_customer_master_cache():
    """Load customer_master.csv into an in-memory dict keyed by customer_code."""
    global customer_master_cache
    customer_master_cache = {}
    if not os.path.isfile(CUSTOMER_MASTER_CSV):
        print(f"Customer master CSV not found at {CUSTOMER_MASTER_CSV}")
        return
    try:
        with open(CUSTOMER_MASTER_CSV, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = row.get('customer_code', '').strip()
                if code:
                    customer_master_cache[code] = dict(row)
        print(f"Loaded customer master: {len(customer_master_cache)} customers.")
    except Exception as e:
        print(f"Error loading customer master: {e}")

load_customer_master_cache()

def load_archived_history_cache():
    global archived_history_cache, archived_qty_cache, archived_last_sale_cache, customer_activity_cache
    # Build new caches locally, then swap atomically to avoid serving empty data
    new_history = defaultdict(list)
    new_qty = {}
    new_last_sale = {}
    new_customer_activity = defaultdict(list)
    csv_file_path = os.path.join(ARCHIVED_LEDGER_DIR, 'stock_ledger_full.csv')
    csv_new_path = csv_file_path + '.new'
    
    # Prefer the .new file if it exists (written by extraction script to avoid lock conflicts)
    if os.path.isfile(csv_new_path):
        # Try to replace the original with the .new file
        try:
            os.replace(csv_new_path, csv_file_path)
            print(f"Swapped {csv_new_path} -> {csv_file_path}")
        except OSError:
            # If swap fails (file locked), just read from the .new file directly
            csv_file_path = csv_new_path
            print(f"Using .new file directly (original is locked)")
    
    if not os.path.isfile(csv_file_path):
        print(f"Archived history CSV not found at {csv_file_path}")
        return

    print("Loading archived history cache...")
    try:
        with open(csv_file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            last_seen_date = ''
            for r in reader:
                # Update last unseen date
                curr_date = r.get('date', '').strip()
                if curr_date:
                    last_seen_date = curr_date
                else:
                    curr_date = last_seen_date

                row_sku = r.get('sku', '').strip()
                row_type = r.get('sku_type', '').strip()
                if not row_sku:
                    continue
                    
                balance = float(r.get('running_balance', 0) or 0)
                new_history[(row_sku, row_type)].append({
                    'date': curr_date,
                    'doc_ref': r.get('doc_ref', ''),
                    'category_name': r.get('category_name', ''),
                    'from_to': r.get('from_to', '').strip(),
                    'qty_in': float(r.get('qty_in', 0) or 0),
                    'qty_out': float(r.get('qty_out', 0) or 0),
                    'running_balance': balance,
                    'unit_price': float(r.get('unit_price', 0) or 0)
                })
                
                from_to = r.get('from_to', '').strip()
                if from_to:
                    new_customer_activity[from_to].append({
                        'date': curr_date,
                        'doc_ref': r.get('doc_ref', ''),
                        'category_name': r.get('category_name', ''),
                        'sku': row_sku,
                        'name_en': r.get('name_en', ''),
                        'qty_in': float(r.get('qty_in', 0) or 0),
                        'qty_out': float(r.get('qty_out', 0) or 0),
                        'unit_price': float(r.get('unit_price', 0) or 0)
                    })
                    
                # Track last running balance as on-hand qty
                new_qty[(row_sku, row_type)] = balance
                # Track last sale date (any row with qty_out > 0)
                qty_out = float(r.get('qty_out', 0) or 0)
                if qty_out > 0 and curr_date:
                    new_last_sale[(row_sku, row_type)] = curr_date
        print(f"Loaded archived history for {len(new_history)} unique parts.")
        print(f"Loaded customer activity for {len(new_customer_activity)} customers.")

        # Atomic swap: replace all global caches at once
        with _cache_lock:
            archived_history_cache = new_history
            archived_qty_cache = new_qty
            archived_last_sale_cache = new_last_sale
            customer_activity_cache = new_customer_activity
    except Exception as e:
        print(f"Error reading archived history: {e}")

    # Write CSV data into the products table so SQL sort/pagination works correctly
    _sync_csv_data_to_db()
    _build_moves_list()

def _sync_csv_data_to_db():
    """Write CSV-sourced on_hand_qty and last_sold_date into the products table."""
    # Snapshot cache refs under lock for thread safety
    with _cache_lock:
        _qty_snap = dict(archived_qty_cache)
        _sale_snap = dict(archived_last_sale_cache)
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Add columns if they don't exist
        try:
            cursor.execute('ALTER TABLE products ADD COLUMN csv_on_hand_qty REAL')
        except Exception:
            pass  # Column already exists
        try:
            cursor.execute('ALTER TABLE products ADD COLUMN csv_last_sold_date TEXT')
        except Exception:
            pass  # Column already exists
        try:
            cursor.execute('ALTER TABLE products ADD COLUMN csv_last_sold_detected_at TEXT')
        except Exception:
            pass  # Column already exists

        # Clear old values (preserve csv_last_sold_detected_at — it accumulates through the day)
        cursor.execute('UPDATE products SET csv_on_hand_qty = NULL, csv_last_sold_date = NULL')

        # Batch update from snapshots
        for (sku, sku_type), qty in _qty_snap.items():
            cursor.execute(
                'UPDATE products SET csv_on_hand_qty = ? WHERE part_code = ? AND suffix = ?',
                (qty, sku, sku_type)
            )
        for (sku, sku_type), sale_date in _sale_snap.items():
            cursor.execute(
                'UPDATE products SET csv_last_sold_date = ? WHERE part_code = ? AND suffix = ?',
                (sale_date, sku, sku_type)
            )
        conn.commit()
        conn.close()
        print(f"Synced CSV data to products table: {len(_qty_snap)} qty values, {len(_sale_snap)} sale dates.")
    except Exception as e:
        print(f"Error syncing CSV data to DB: {e}")

@app.route('/api/products/<sku>/archived-history')
def get_archived_history(sku):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT part_code, suffix FROM products WHERE sku = ?', (sku,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({'error': 'Product not found'}), 404

    part_code = row['part_code']
    suffix = row['suffix']

    global archived_history_cache
    if archived_history_cache is None:
        load_archived_history_cache()

    # Snapshot cache ref under lock for thread safety
    with _cache_lock:
        _hist_snap = archived_history_cache

    history = _hist_snap.get((part_code, suffix), [])

    # Enrich each entry with customer name from customer_master_cache
    enriched = []
    for h in history:
        entry = dict(h)
        from_to_code = h.get('from_to', '').strip()
        if from_to_code and from_to_code in customer_master_cache:
            entry['from_to_name'] = customer_master_cache[from_to_code].get('customer_name', '')
        enriched.append(entry)

    return jsonify(enriched)

@app.route('/api/customer-activity/<customer_id>')
def get_customer_activity(customer_id):
    global archived_history_cache, customer_activity_cache
    if archived_history_cache is None:
        load_archived_history_cache()
    
    history = customer_activity_cache.get(customer_id, [])
    # Sort by date descending
    history_sorted = sorted(history, key=lambda x: x['date'], reverse=True)
    return jsonify(history_sorted)


# ─── Customer Master API ────────────────────────────────────────────────────

@app.route('/api/customers')
def get_customers():
    """Paginated customer list with search. Returns master info + txn count."""
    global archived_history_cache, customer_activity_cache
    if archived_history_cache is None:
        load_archived_history_cache()

    search = request.args.get('search', '').strip().lower()
    page = int(request.args.get('page', 1))
    per_page = max(1, int(request.args.get('per_page', 50)))

    # Build filtered list
    all_customers = list(customer_master_cache.values())
    if search:
        filtered = []
        for c in all_customers:
            searchable = ' '.join([
                c.get('customer_code', ''),
                c.get('customer_name', ''),
                c.get('phone', ''),
                c.get('tax_id', ''),
                c.get('address', ''),
                c.get('contact_person', ''),
            ]).lower()
            if search in searchable:
                filtered.append(c)
    else:
        filtered = all_customers

    # Sort by customer_code
    filtered.sort(key=lambda x: x.get('customer_code', ''))

    total = len(filtered)
    total_pages = math.ceil(total / per_page) if per_page else 1
    offset = (page - 1) * per_page
    page_items = filtered[offset:offset + per_page]

    # Enrich with transaction count from activity cache
    items = []
    for c in page_items:
        code = c.get('customer_code', '')
        txn_count = len(customer_activity_cache.get(code, []))
        item = dict(c)
        item['txn_count'] = txn_count
        items.append(item)

    return jsonify({
        'items': items,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': total_pages
    })


@app.route('/api/customers/<code>')
def get_customer_detail(code):
    """Return customer master info + transaction history."""
    global archived_history_cache, customer_activity_cache
    if archived_history_cache is None:
        load_archived_history_cache()

    master = customer_master_cache.get(code)
    if not master:
        return jsonify({'error': 'Customer not found'}), 404

    history = customer_activity_cache.get(code, [])
    history_sorted = sorted(history, key=lambda x: x['date'], reverse=True)

    return jsonify({
        'customer': dict(master),
        'transactions': history_sorted,
        'txn_count': len(history_sorted)
    })


@app.route('/api/refresh-customer-master', methods=['POST'])
def refresh_customer_master():
    """Run extract_customer_master.py, then reload the customer master cache."""
    try:
        script_path = os.path.join(os.path.dirname(__file__), 'python script', 'extract_customer_master.py')
        if not os.path.isfile(script_path):
            return jsonify({'success': False, 'message': f'Script not found: {script_path}'}), 500

        print(f"Running customer master extraction: {script_path}")
        result = subprocess.run([sys.executable, script_path], capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            print("Customer master extraction failed.")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return jsonify({'success': False, 'message': 'Script execution failed', 'details': result.stderr}), 500

        load_customer_master_cache()

        return jsonify({
            'success': True,
            'message': f'Customer master refreshed: {len(customer_master_cache)} customers loaded.'
        })
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'message': 'Script timed out after 5 minutes'}), 500
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


# ─── Invoice Data Cache ─────────────────────────────────────────────────────
# Note: INVOICE_DIR is defined at the top of the file (line 28)

invoice_headers_cache = []   # list of dicts from invoice_headers.csv
invoice_line_items_cache = defaultdict(list)  # invoice_number -> list of line items

def load_invoice_cache():
    """Load invoice_headers.csv and invoice_line_items.csv into memory."""
    global invoice_headers_cache, invoice_line_items_cache
    invoice_headers_cache = []
    invoice_line_items_cache = defaultdict(list)

    headers_csv = os.path.join(INVOICE_DIR, 'invoice_headers.csv')
    if not os.path.isfile(headers_csv):
        print(f"Invoice headers CSV not found at {headers_csv}")
        return

    try:
        with open(headers_csv, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert numeric fields
                for fld in ('subtotal', 'net_amount', 'vat_rate', 'vat_amount', 'grand_total', 'discount'):
                    try:
                        row[fld] = float(row.get(fld, 0) or 0)
                    except (ValueError, TypeError):
                        row[fld] = 0.0
                try:
                    row['credit_days'] = int(float(row.get('credit_days', 0) or 0))
                except (ValueError, TypeError):
                    row['credit_days'] = 0
                invoice_headers_cache.append(row)
        print(f"Loaded invoice headers: {len(invoice_headers_cache)} invoices.")
    except Exception as e:
        print(f"Error loading invoice headers: {e}")

    line_items_csv = os.path.join(INVOICE_DIR, 'invoice_line_items.csv')
    if not os.path.isfile(line_items_csv):
        print(f"Invoice line items CSV not found at {line_items_csv}")
        return

    try:
        with open(line_items_csv, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                for fld in ('qty', 'unit_cost', 'unit_price', 'total_cost', 'total_price', 'line_number'):
                    try:
                        row[fld] = float(row.get(fld, 0) or 0)
                    except (ValueError, TypeError):
                        row[fld] = 0.0
                iv_ref = row.get('iv_doc_ref', '').strip()
                if iv_ref:
                    invoice_line_items_cache[iv_ref].append(row)
                    count += 1
        print(f"Loaded invoice line items: {count} items across {len(invoice_line_items_cache)} invoices.")
    except Exception as e:
        print(f"Error loading invoice line items: {e}")

load_invoice_cache()


@app.route('/api/invoices')
def get_invoices():
    """Paginated invoice list with search and doc_type filter."""
    search = request.args.get('search', '').strip().lower()
    doc_type = request.args.get('doc_type', '').strip().upper()  # IV, OR, or empty=all
    page = int(request.args.get('page', 1))
    per_page = max(1, int(request.args.get('per_page', 50)))
    sort_by = request.args.get('sort', 'invoice_date').strip()
    sort_dir = request.args.get('dir', 'desc').lower()

    filtered = []
    for h in invoice_headers_cache:
        # Doc type filter
        if doc_type and h.get('doc_type', '') != doc_type:
            continue
        # Search filter
        if search:
            searchable = ' '.join([
                h.get('invoice_number', ''),
                h.get('customer_code', ''),
                h.get('customer_name', ''),
                h.get('salesperson_code', ''),
                h.get('delivery_address', ''),
            ]).lower()
            if search not in searchable:
                continue
        filtered.append(h)

    # Sort
    sort_keys = {
        'invoice_date': lambda x: x.get('invoice_date', ''),
        'invoice_number': lambda x: x.get('invoice_number', ''),
        'customer_code': lambda x: x.get('customer_code', ''),
        'customer_name': lambda x: x.get('customer_name', ''),
        'grand_total': lambda x: x.get('grand_total', 0),
        'vat_amount': lambda x: x.get('vat_amount', 0),
        'subtotal': lambda x: x.get('subtotal', 0),
    }
    if sort_by in sort_keys:
        filtered.sort(key=sort_keys[sort_by], reverse=(sort_dir == 'desc'))

    total = len(filtered)
    total_pages = math.ceil(total / per_page) if per_page else 1
    offset = (page - 1) * per_page
    page_items = filtered[offset:offset + per_page]

    # Enrich with line item count
    items = []
    for h in page_items:
        inv_num = h.get('invoice_number', '')
        item = dict(h)
        item['line_item_count'] = len(invoice_line_items_cache.get(inv_num, []))
        items.append(item)

    return jsonify({
        'items': items,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': total_pages
    })


@app.route('/api/invoices/<invoice_number>')
def get_invoice_detail(invoice_number):
    """Return invoice header + line items."""
    header = None
    for h in invoice_headers_cache:
        if h.get('invoice_number', '') == invoice_number:
            header = dict(h)
            break

    if not header:
        return jsonify({'error': 'Invoice not found'}), 404

    line_items = invoice_line_items_cache.get(invoice_number, [])
    # Sort line items by line_number
    line_items_sorted = sorted(line_items, key=lambda x: x.get('line_number', 0))

    return jsonify({
        'header': header,
        'line_items': [dict(li) for li in line_items_sorted],
        'line_item_count': len(line_items_sorted)
    })


@app.route('/api/refresh-invoices', methods=['POST'])
def refresh_invoices():
    """Run extract_invoice.py, then reload the invoice caches."""
    try:
        script_path = os.path.join(os.path.dirname(__file__), 'python script', 'extract_invoice.py')
        if not os.path.isfile(script_path):
            return jsonify({'success': False, 'message': f'Script not found: {script_path}'}), 500

        print(f"Running invoice extraction: {script_path}")
        result = subprocess.run([sys.executable, script_path], capture_output=True, text=True, timeout=600)

        if result.returncode != 0:
            print("Invoice extraction failed.")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return jsonify({'success': False, 'message': 'Script execution failed', 'details': result.stderr}), 500

        load_invoice_cache()

        return jsonify({
            'success': True,
            'message': f'Invoice data refreshed: {len(invoice_headers_cache)} invoices loaded.'
        })
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'message': 'Script timed out after 10 minutes'}), 500
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/refresh-ledger', methods=['POST'])
def refresh_ledger():
    """Run the ledger extraction script, reload the CSV, and sync data to the DB."""
    try:
        # 1. Run the Python extraction script (writes to .new temp file)
        script_path = os.path.join(os.path.dirname(__file__), 'python script', 'extract_stock_ledger_v4.py')
        print(f"Running ledger extraction script: {script_path}")
        result = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
        
        if result.returncode != 0:
            print("Extraction script failed.")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return jsonify({'success': False, 'message': 'Script execution failed', 'details': result.stderr}), 500
        
        # 2. Reload the cache (load_archived_history_cache handles .new file swap/fallback)
        load_archived_history_cache()
        
        return jsonify({
            'success': True,
            'message': f'Script ran successfully. Refreshed ledger data: {len(archived_qty_cache)} qty values, {len(archived_last_sale_cache)} sale dates.'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/refresh-master', methods=['POST'])
def refresh_master():
    """Run extract_product_master.py, then load product_master_active.csv into the products table."""
    try:
        # 1. Run the extraction script
        script_path = os.path.join(os.path.dirname(__file__), 'python script', 'extract_product_master.py')
        if not os.path.isfile(script_path):
            return jsonify({'success': False, 'message': f'Script not found: {script_path}'}), 500

        print(f"Running product master extraction: {script_path}")
        result = subprocess.run([sys.executable, script_path], capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            print("Product master extraction failed.")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return jsonify({'success': False, 'message': 'Script execution failed', 'details': result.stderr}), 500

        # 2. Read the generated CSV
        csv_path = os.path.join(os.path.dirname(__file__), 'product master table', 'product_master_active.csv')
        if not os.path.isfile(csv_path):
            return jsonify({'success': False, 'message': 'product_master_active.csv not found after extraction'}), 500

        products = []
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                products.append(row)

        if not products:
            return jsonify({'success': False, 'message': 'No products found in CSV'}), 500

        # 3. Rebuild the products table
        conn = get_db_connection()
        cursor = conn.cursor()

        # Clear existing products (flags table is preserved)
        cursor.execute('DELETE FROM products')

        # Parse numeric fields safely
        def safe_float(val):
            try:
                return float(str(val).replace(',', '')) if val else 0.0
            except (ValueError, TypeError):
                return 0.0

        count = 0
        for p in products:
            sku_code = p.get('sku', '').strip()
            suffix = p.get('type', '').strip()
            if not sku_code or not suffix:
                continue

            sku = f"{sku_code}_{suffix}"

            # Find thumbnail (strip trailing 'R' for image lookup)
            image_lookup_part = sku_code
            if image_lookup_part.endswith('R'):
                image_lookup_part = image_lookup_part[:-1]
            thumbnail, image_count = find_thumbnail(image_lookup_part)
            if not thumbnail and image_lookup_part != sku_code:
                thumbnail, image_count = find_thumbnail(sku_code)

            qty = safe_float(p.get('qty_on_hand', 0))
            sale_price = safe_float(p.get('selling_price', 0))
            unit_cost = safe_float(p.get('unit_cost', 0))
            market_price = safe_float(p.get('market_price', 0))

            cursor.execute('''
                INSERT OR REPLACE INTO products (
                    sku, part_code, suffix, suffix_label, name_eng, name_thai, size, brand,
                    qty, sale_price, unit_cost, market_price, thumbnail, image_count, locations
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                sku, sku_code, suffix, SUFFIX_MAP.get(suffix, 'Unknown'),
                p.get('name_en', ''), p.get('name_th', ''),
                p.get('specification', ''), p.get('brand', ''),
                int(qty), sale_price, unit_cost, market_price,
                thumbnail or '', image_count, p.get('warehouse', '')
            ))
            count += 1

        conn.commit()
        conn.close()

        # 4. Reload archived ledger cache to sync CSV-based qty/dates to the new products
        global archived_history_cache
        archived_history_cache = None  # Force full reload on next access
        load_archived_history_cache()

        print(f"Product master refreshed: {count} active products loaded from CSV.")
        return jsonify({
            'success': True,
            'message': f'Product master refreshed: {count} active products loaded.'
        })
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'message': 'Script timed out after 5 minutes'}), 500
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500



# ─── Build flat moves list from archived ledger ─────────────────────────────
all_ledger_moves = []   # populated by _build_moves_list()

def _build_moves_list():
    """Build a flat list of all moves from the archived_history_cache for the moves tab."""
    global all_ledger_moves
    # Snapshot cache ref under lock
    with _cache_lock:
        _hist_snap = archived_history_cache
    if _hist_snap is None:
        return
    new_moves = []
    for (part_code, sku_type), entries in _hist_snap.items():
        for entry in entries:
            if entry['qty_in'] == 0 and entry['qty_out'] == 0:
                continue  # Skip zero-change rows
            new_moves.append({
                'part_code': part_code,
                'sku_type': sku_type,
                'date': entry['date'],
                'doc_ref': entry.get('doc_ref', ''),
                'category_name': entry.get('category_name', ''),
                'qty_in': entry['qty_in'],
                'qty_out': entry['qty_out'],
                'unit_price': entry['unit_price'],
                'running_balance': entry['running_balance'],
            })
    # Sort by date descending by default
    new_moves.sort(key=lambda x: x['date'], reverse=True)
    # Atomic swap — readers always see a complete list
    all_ledger_moves = new_moves
    print(f"Built moves list: {len(all_ledger_moves)} move entries.")

# ─── Sort helpers ────────────────────────────────────────────────────────────

def _flags_order(sort_by, sort_dir):
    """Return a safe ORDER BY clause for the flags endpoint."""
    col_map = {
        'part_code': 'p.part_code',
        'name_eng': 'p.name_eng',
        'brand': 'p.brand',
        'system_qty': 'p.qty',
        'flag_type': 'f.flag_type',
        'flagged_at': 'f.flagged_at',
        'flagged_by': 'f.flagged_by',
    }
    d = 'DESC' if sort_dir == 'desc' else 'ASC'
    if sort_by in col_map:
        return f"{col_map[sort_by]} {d}"
    return "f.flagged_at DESC"

@app.route('/api/moves')
def get_all_moves():
    global archived_history_cache
    if archived_history_cache is None:
        load_archived_history_cache()
    if not all_ledger_moves:
        _build_moves_list()

    search = request.args.get('search', '').strip().lower()
    move_type = request.args.get('type', 'all').lower()  # 'all', 'in', 'out'
    sort_by = request.args.get('sort', '').strip()
    sort_dir = request.args.get('dir', 'desc').lower()
    page = int(request.args.get('page', 1))
    per_page = max(1, int(request.args.get('per_page', 50)))

    # Build a product lookup from DB for name/brand/thumbnail
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT part_code, suffix, name_eng, name_thai, brand, thumbnail, sku FROM products')
    product_map = {}
    for row in cursor.fetchall():
        product_map[(row['part_code'], row['suffix'])] = dict(row)
    conn.close()

    # Filter
    filtered = []
    for m in all_ledger_moves:
        # Type filter
        if move_type == 'in' and m['qty_in'] <= 0:
            continue
        if move_type == 'out' and m['qty_out'] <= 0:
            continue

        # Search filter
        if search:
            prod = product_map.get((m['part_code'], m['sku_type']), {})
            searchable = (
                m['part_code'].lower() + ' ' +
                prod.get('name_eng', '').lower() + ' ' +
                prod.get('name_thai', '').lower() + ' ' +
                m.get('doc_ref', '').lower() + ' ' +
                m.get('category_name', '').lower()
            )
            if search not in searchable:
                continue

        filtered.append(m)

    # Sort
    sort_keys = {
        'date': lambda x: x['date'],
        'part_code': lambda x: x['part_code'],
        'qty_in': lambda x: x['qty_in'],
        'qty_out': lambda x: x['qty_out'],
        'unit_price': lambda x: x['unit_price'],
        'running_balance': lambda x: x['running_balance'],
        'doc_ref': lambda x: x.get('doc_ref', ''),
        'category_name': lambda x: x.get('category_name', ''),
    }
    if sort_by in sort_keys:
        filtered.sort(key=sort_keys[sort_by], reverse=(sort_dir == 'desc'))

    total_items = len(filtered)
    total_pages = math.ceil(total_items / per_page) if per_page else 1

    # Paginate
    offset = (page - 1) * per_page
    page_items = filtered[offset:offset + per_page]

    # Enrich with product info
    result = []
    for m in page_items:
        prod = product_map.get((m['part_code'], m['sku_type']), {})
        result.append({
            'date': m['date'],
            'part_code': m['part_code'],
            'sku_type': m['sku_type'],
            'doc_ref': m.get('doc_ref', ''),
            'category_name': m.get('category_name', ''),
            'qty_in': m['qty_in'],
            'qty_out': m['qty_out'],
            'unit_price': m['unit_price'],
            'running_balance': m['running_balance'],
            'name_eng': prod.get('name_eng', ''),
            'name_thai': prod.get('name_thai', ''),
            'brand': prod.get('brand', ''),
            'thumbnail': prod.get('thumbnail', ''),
            'sku': prod.get('sku', f"{m['part_code']}_{m['sku_type']}"),
        })

    return jsonify({
        'items': result,
        'total': total_items,
        'page': page,
        'per_page': per_page,
        'total_pages': total_pages
    })

# ─── Stock Flags API ───────────────────────────────────────────────────────────

@app.route('/api/products/<sku>/flag', methods=['POST'])
def flag_product(sku):
    data = request.json or {}
    flag_type = data.get('flag_type')
    note = data.get('note', '')
    flagged_by = session.get('user', '')

    if not flag_type or flag_type not in ['out_of_stock', 'less_than', 'more_than']:
        return jsonify({'error': 'Invalid or missing flag_type'}), 400

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Ensure product exists
        cursor.execute('SELECT id FROM products WHERE sku = ?', (sku,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Product not found'}), 404

        cursor.execute('''
            INSERT INTO stock_flags (sku, flag_type, note, flagged_at, flagged_by)
            VALUES (?, ?, ?, datetime('now', 'localtime'), ?)
            ON CONFLICT(sku) DO UPDATE SET
                flag_type = excluded.flag_type,
                note = excluded.note,
                flagged_at = datetime('now', 'localtime'),
                flagged_by = excluded.flagged_by
        ''', (sku, flag_type, note, flagged_by))
        
        conn.commit()
    finally:
        conn.close()
    print(f"[Flags] Product {sku} flagged as '{flag_type}' by {flagged_by}")
    return jsonify({'status': 'success', 'message': 'Product flagged'})

@app.route('/api/products/<sku>/flag', methods=['DELETE'])
@admin_required
def unflag_product(sku):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM stock_flags WHERE sku = ?', (sku,))
    conn.commit()
    conn.close()
    username = session.get('user', 'unknown')
    print(f"[Flags] Product {sku} resolved (unflagged) by {username}")
    return jsonify({'status': 'success', 'message': 'Product unflagged'})

@app.route('/api/flags')
def get_flags():
    search = request.args.get('search', '').strip()
    sort_by = request.args.get('sort', '').strip()
    sort_dir = request.args.get('dir', 'desc').lower()
    page = int(request.args.get('page', 1))
    per_page = max(1, int(request.args.get('per_page', 50)))

    query_select = """
        SELECT f.id as flag_id, f.flag_type, f.note as flag_note, f.flagged_at, f.flagged_by,
               p.*, p.qty as system_qty
        FROM stock_flags f
        JOIN products p ON f.sku = p.sku
    """
    
    where_clause = " WHERE 1=1"
    params = []

    if search:
        search_term = f"%{search}%"
        where_clause += " AND (p.part_code LIKE ? OR p.name_eng LIKE ? OR p.name_thai LIKE ? OR p.sku LIKE ?)"
        params.extend([search_term, search_term, search_term, search_term])

    count_query = "SELECT COUNT(*) FROM stock_flags f JOIN products p ON f.sku = p.sku" + where_clause
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(count_query, params)
    total_items = cursor.fetchone()[0]

    query = query_select + where_clause + f" ORDER BY {_flags_order(sort_by, sort_dir)} LIMIT ? OFFSET ?"
    query_params = list(params)
    query_params.extend([per_page, (page - 1) * per_page])

    cursor.execute(query, query_params)
    flags = [dict(row) for row in cursor.fetchall()]
    conn.close()

    total_pages = math.ceil(total_items / per_page) if per_page else 1

    return jsonify({
        'items': flags,
        'total': total_items,
        'page': page,
        'per_page': per_page,
        'total_pages': total_pages
    })


# --- Titles Cache Logic ---
TITLES_CSV_PATH = os.path.join(os.path.dirname(__file__), 'product titles', 'extracted_titles.csv')
TITLES_CACHE_PATH = os.path.join(os.path.dirname(__file__), 'titles_cache.json')
titles_dict = {}

def load_titles_cache():
    global titles_dict
    if os.path.exists(TITLES_CACHE_PATH):
        print("Loading titles cache from JSON...")
        try:
            with open(TITLES_CACHE_PATH, "r", encoding="utf-8") as f:
                titles_dict = json.load(f)
            print(f"Loaded titles for {len(titles_dict)} parts.")
        except Exception as e:
            print(f"Error loading titles cache: {e}")
            titles_dict = {}
    elif os.path.exists(TITLES_CSV_PATH):
        print(f"Building titles cache from {TITLES_CSV_PATH}...")
        temp_dict = defaultdict(set)
        try:
            with open(TITLES_CSV_PATH, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    part_no = row.get("Part Number", "").strip()
                    title = row.get("Title", "").strip()
                    if part_no and title:
                        temp_dict[part_no].add(title)
            
            # Convert sets to lists and save
            titles_dict = {k: list(v) for k, v in temp_dict.items()}
            with open(TITLES_CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(titles_dict, f, ensure_ascii=False)
            print(f"Built and saved titles cache for {len(titles_dict)} parts.")
        except Exception as e:
            print(f"Error building titles cache: {e}")
            titles_dict = {}
    else:
        print("No titles CSV or cache found.")

load_titles_cache()

@app.route('/api/products/<sku>/titles')
def get_product_titles(sku):
    conn = get_db_connection()
    product = conn.execute('SELECT part_code FROM products WHERE sku = ?', (sku,)).fetchone()
    conn.close()
    
    if not product:
        return jsonify({'error': 'Product not found'}), 404
        
    part_code = product['part_code']
    
    # First attempt: exact match
    titles = titles_dict.get(part_code, [])
    
    # Second attempt: fallback to base part code if it ends in a letter (e.g., 04312-10010-71R -> 04312-10010-71)
    if not titles and len(part_code) > 0 and part_code[-1].isalpha():
        base_part = part_code[:-1]
        titles = titles_dict.get(base_part, [])
    
    return jsonify(titles)

# --- Engine List ---
ENGINE_LIST_PATH = os.path.join(os.path.dirname(__file__), 'engine list', 'engine list.csv')
engine_list = []

def load_engine_list():
    global engine_list
    try:
        with open(ENGINE_LIST_PATH, "r", encoding="utf-8") as f:
            raw = f.read().strip()
            engine_list = [e.strip() for e in raw.split(",") if e.strip()]
        print(f"Loaded {len(engine_list)} engine models.")
    except Exception as e:
        print(f"Error loading engine list: {e}")
        engine_list = []

load_engine_list()

@app.route('/api/engine-list')
def get_engine_list():
    return jsonify(engine_list)

# --- Forklift Brand List ---
FORKLIFT_BRAND_PATH = os.path.join(os.path.dirname(__file__), 'forklift brand', 'forklift brand.csv')
forklift_brands = []

def load_forklift_brands():
    global forklift_brands
    try:
        with open(FORKLIFT_BRAND_PATH, "r", encoding="utf-8") as f:
            raw = f.read().strip()
            # Handle trailing period
            if raw.endswith('.'):
                raw = raw[:-1]
            forklift_brands = [b.strip() for b in raw.split(",") if b.strip()]
        print(f"Loaded {len(forklift_brands)} forklift brands.")
    except Exception as e:
        print(f"Error loading forklift brands: {e}")
        forklift_brands = []

load_forklift_brands()

@app.route('/api/forklift-brands')
def get_forklift_brands():
    return jsonify(forklift_brands)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Inventory Management Server')
    parser.add_argument('--production', action='store_true',
                        help='Run with Waitress (production mode). Default: Flask dev server.')
    parser.add_argument('--port', type=int, default=8080, help='Port to listen on (default: 8080)')
    parser.add_argument('--threads', type=int, default=32,
                        help='Number of Waitress threads in production mode (default: 32)')
    args = parser.parse_args()

    print("Starting Inventory Management Server...")
    # Eagerly load CSV cache and sync to DB at startup
    load_archived_history_cache()
    # Start background file watcher for auto-sync from Z:\ server
    start_file_watcher()
    # Start auto-backup scheduler
    _start_auto_backup_scheduler()
    print(f"Available at: http://localhost:{args.port}")
    print("[AutoSync] Background file watcher active — monitoring Z:\\ for changes every", FILE_CHECK_INTERVAL, "seconds")

    if args.production:
        try:
            from waitress import serve
        except ImportError:
            print("ERROR: Waitress is not installed. Install it with: pip install waitress")
            print("       Falling back to Flask development server...")
            app.run(host='0.0.0.0', port=args.port, debug=True, use_reloader=False)
            sys.exit(1)
        print(f"[Production] Running with Waitress ({args.threads} threads)")
        serve(app, host='0.0.0.0', port=args.port, threads=args.threads)
    else:
        print("[Dev] Running with Flask development server (debug=True)")
        app.run(host='0.0.0.0', port=args.port, debug=True, use_reloader=False)
