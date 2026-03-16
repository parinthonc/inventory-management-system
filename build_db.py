import sqlite3
import os
import re
import glob
import configparser

# ─── Load configuration (cascade: default → config.ini → local overrides) ────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

config = configparser.ConfigParser()
# Load in order: each file overrides values from the previous one.
#   1. config.default.ini  – shared template (tracked by git)
#   2. config.ini           – backward compat (gitignored going forward)
#   3. config.local.ini     – per-machine overrides (gitignored)
_config_files_loaded = config.read([
    os.path.join(BASE_DIR, 'config.default.ini'),
    os.path.join(BASE_DIR, 'config.ini'),
    os.path.join(BASE_DIR, 'config.local.ini'),
])
if _config_files_loaded:
    print(f"[Config] Loaded: {', '.join(os.path.basename(f) for f in _config_files_loaded)}")
else:
    print("[Config] WARNING: No config files found!")

# Image directory (custom/user-uploaded images only)
IMAGE_DIR_CUSTOM = config.get('images', 'custom_dir', fallback='').strip()
if IMAGE_DIR_CUSTOM and not os.path.isabs(IMAGE_DIR_CUSTOM):
    IMAGE_DIR_CUSTOM = os.path.join(BASE_DIR, IMAGE_DIR_CUSTOM)
if IMAGE_DIR_CUSTOM:
    os.makedirs(IMAGE_DIR_CUSTOM, exist_ok=True)
    print(f"[Config] Custom image dir: {IMAGE_DIR_CUSTOM}")

# IMAGE_DIRS kept as a list for backward compatibility with server.py
IMAGE_DIRS = [IMAGE_DIR_CUSTOM] if IMAGE_DIR_CUSTOM else []

# Other paths
ZIND_DIR = BASE_DIR

def _resolve_path(raw_path, default):
    """Resolve a config path: if relative, make it relative to BASE_DIR."""
    p = raw_path.strip() if raw_path else default
    if not os.path.isabs(p):
        p = os.path.join(BASE_DIR, p)
    return p

ARCHIVE_DIR = _resolve_path(config.get('paths', 'archive_dir', fallback=''), os.path.join(ZIND_DIR, 'zind archive'))
ARCHIVED_LEDGER_DIR = _resolve_path(config.get('paths', 'archived_ledger_dir', fallback=''), os.path.join(ZIND_DIR, 'archived ledger'))
DB_FILE = _resolve_path(config.get('paths', 'db_file', fallback=''), os.path.join(ZIND_DIR, 'inventory.db'))
LOGO_FILE = _resolve_path(config.get('paths', 'logo_file', fallback=''), os.path.join(ZIND_DIR, 'logo', 'logo.png'))


# Suffix meanings
SUFFIX_MAP = {
    'G': 'Genuine (OEM)',
    'N': 'Japanese Made',
    'L': 'Locally Made',
    'R': 'Chinese Made',
    'C': 'Chinese Budget'
}

def parse_number(num_str):
    """Parse comma-separated number string to float."""
    if not num_str:
        return 0.0
    try:
        first_token = num_str.strip().split()[0]
        return float(first_token.replace(',', ''))
    except (ValueError, IndexError):
        return 0.0

def extract_date_from_filename(filename):
    """Extract Gregorian date from ZIND filename (BE year)."""
    m = re.match(r'ZIND\d+_(\d{4})-(\d{2})-(\d{2})_', filename)
    if not m:
        return None
    year_be = int(m.group(1))
    month = int(m.group(2))
    day = int(m.group(3))
    year_ce = year_be - 543
    return f"{year_ce:04d}-{month:02d}-{day:02d}"

def find_thumbnail(base_part_number):
    """Find the first alphabetical image file in the part's custom image directory.
    Scans IMAGE_DIR_CUSTOM for any folder starting with the base part number
    (e.g. base_part_number='04111-20220-71' matches folder '04111-20220-71_G').
    Returns (relative_path, file_count) or (None, 0)."""
    if not IMAGE_DIR_CUSTOM or not os.path.isdir(IMAGE_DIR_CUSTOM):
        return None, 0

    # Look for any SKU folder that starts with this part number
    prefix = base_part_number + '_'
    for folder_name in sorted(os.listdir(IMAGE_DIR_CUSTOM)):
        if folder_name.startswith(prefix) or folder_name == base_part_number:
            folder_path = os.path.join(IMAGE_DIR_CUSTOM, folder_name)
            if os.path.isdir(folder_path):
                files = [f for f in os.listdir(folder_path)
                         if os.path.isfile(os.path.join(folder_path, f))
                         and not f.startswith('_')
                         and f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
                if files:
                    files.sort()
                    # Return path relative to custom dir, prefixed with custom/
                    return f'custom/{folder_name}/{files[0]}', len(files)

    return None, 0

def parse_zind_file(filepath):
    """Parse a ZIND file and return dict of {sku: {fields...}}."""
    with open(filepath, 'rb') as f:
        raw_data = f.read()
    try:
        text = raw_data.decode('latin-1').encode('latin-1').decode('cp874')
    except:
        text = raw_data.decode('cp874', errors='ignore')

    items = {}
    last_sku = None

    for line in text.splitlines():
        line = line.strip()
        if not line.startswith('D|'):
            continue
        fields = [f.strip() for f in line.split('|')]
        if len(fields) < 8:
            continue

        part_code = fields[1].replace("Code.", "").strip()
        warehouse = fields[3].strip() if len(fields) > 3 else ''

        # Continuation row
        if not part_code:
            if last_sku and last_sku in items:
                qty = int(parse_number(fields[8])) if len(fields) > 8 else 0
                items[last_sku]['qty'] += qty
                if warehouse:
                    items[last_sku]['locations_set'].add(warehouse)
            continue

        suffix = fields[2].strip()
        sku = f"{part_code}_{suffix}"

        items[sku] = {
            'sku': sku,
            'part_code': part_code,
            'suffix': suffix,
            'suffix_label': SUFFIX_MAP.get(suffix, 'Unknown'),
            'name_eng': fields[4] if len(fields) > 4 else '',
            'name_thai': fields[5] if len(fields) > 5 else '',
            'size': fields[6].replace("Code.", "").strip() if len(fields) > 6 else '',
            'brand': fields[7] if len(fields) > 7 else '',
            'qty': int(parse_number(fields[8])) if len(fields) > 8 else 0,
            'sale_price': parse_number(fields[9]) if len(fields) > 9 else 0.0,
            'unit_cost': parse_number(fields[10]) if len(fields) > 10 else 0.0,
            'market_price': parse_number(fields[11]) if len(fields) > 11 else 0.0,
            'locations_set': {warehouse} if warehouse else set()
        }
        last_sku = sku

    return items

def init_db():
    """Initialize the products table in the SQLite database.
    Preserves other tables (stock_flags, users, audit_log) across rebuilds."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Drop only the products table (preserve flags, users, audit_log)
    cursor.execute('DROP TABLE IF EXISTS products')

    cursor.execute('''
    CREATE TABLE products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku TEXT UNIQUE,
        part_code TEXT,
        suffix TEXT,
        suffix_label TEXT,
        name_eng TEXT,
        name_thai TEXT,
        size TEXT,
        brand TEXT,
        qty INTEGER,
        sale_price REAL,
        unit_cost REAL,
        market_price REAL,
        thumbnail TEXT,
        image_count INTEGER,
        locations TEXT
    )
    ''')

    cursor.execute('CREATE INDEX idx_brand ON products(brand)')
    cursor.execute('CREATE INDEX idx_part_code ON products(part_code)')
    cursor.execute('CREATE INDEX idx_name_eng ON products(name_eng)')
    cursor.execute('CREATE INDEX idx_name_thai ON products(name_thai)')

    conn.commit()
    return conn


def main():
    # 1. Collect all ZIND files
    all_files = []

    # Archive files
    if os.path.isdir(ARCHIVE_DIR):
        for f in sorted(os.listdir(ARCHIVE_DIR)):
            if f.upper().startswith('ZIND') and f.upper().endswith('.TXT'):
                all_files.append(os.path.join(ARCHIVE_DIR, f))

    # Main ZIND file(s) in root dir
    for f in sorted(os.listdir(ZIND_DIR)):
        if f.upper().startswith('ZIND') and f.upper().endswith('.TXT'):
            all_files.append(os.path.join(ZIND_DIR, f))

    print(f"Found {len(all_files)} ZIND files to process.")

    # 2. Initialize DB
    conn = init_db()

    # 3. Use the LATEST ZIND file to populate products table
    latest_file = all_files[-1]  # They are sorted alphabetically = chronologically
    print(f"\nUsing latest file for products: {os.path.basename(latest_file)}")

    items = parse_zind_file(latest_file)

    cursor = conn.cursor()
    count = 0
    for sku, item in items.items():
        # Get images
        image_lookup_part = item['part_code']
        if image_lookup_part.endswith('R'):
            image_lookup_part = image_lookup_part[:-1]
        thumbnail, image_count = find_thumbnail(image_lookup_part)
        if not thumbnail and image_lookup_part != item['part_code']:
            thumbnail, image_count = find_thumbnail(item['part_code'])

        locations = ', '.join(sorted(list(item['locations_set'])))

        cursor.execute('''
            INSERT OR REPLACE INTO products (
                sku, part_code, suffix, suffix_label, name_eng, name_thai, size, brand,
                qty, sale_price, unit_cost, market_price, thumbnail, image_count, locations
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            item['sku'], item['part_code'], item['suffix'], item['suffix_label'],
            item['name_eng'], item['name_thai'], item['size'], item['brand'],
            item['qty'], item['sale_price'], item['unit_cost'], item['market_price'],
            thumbnail or '', image_count, locations
        ))
        count += 1
        if count % 2000 == 0:
            conn.commit()
            print(f"  Inserted {count} products...")

    conn.commit()
    conn.close()
    print(f"\nDone! {count} products loaded.")
    print(f"Database: {DB_FILE}")

if __name__ == '__main__':
    main()
