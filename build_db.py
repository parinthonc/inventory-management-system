import sqlite3
import os
import csv
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
def _resolve_path(raw_path, default):
    """Resolve a config path: if relative, make it relative to BASE_DIR."""
    p = raw_path.strip() if raw_path else default
    if not os.path.isabs(p):
        p = os.path.join(BASE_DIR, p)
    return p

ARCHIVED_LEDGER_DIR = _resolve_path(config.get('paths', 'archived_ledger_dir', fallback=''), os.path.join(BASE_DIR, 'ledger'))
DB_FILE = _resolve_path(config.get('paths', 'db_file', fallback=''), os.path.join(BASE_DIR, 'inventory.db'))
LOGO_FILE = _resolve_path(config.get('paths', 'logo_file', fallback=''), os.path.join(BASE_DIR, 'logo', 'logo.png'))

# CSV data source path
PRODUCT_MASTER_CSV = os.path.join(BASE_DIR, 'product master table', 'product_master_active.csv')

# Suffix meanings
SUFFIX_MAP = {
    'G': 'Genuine (OEM)',
    'N': 'Japanese Made',
    'L': 'Locally Made',
    'R': 'Chinese Made',
    'C': 'Chinese Budget'
}

def find_thumbnail(sku):
    """Find a thumbnail image in the SKU's custom image directory.
    Prefers the _thumb_ version (300px) for faster product list loading.
    Uses the 2nd photo (alphabetically) when multiple photos exist,
    otherwise falls back to the 1st photo.
    Requires an EXACT folder name match (e.g. sku='22673-72031_N' matches only
    folder '22673-72031_N', NOT '22673-72031_G').
    Returns (relative_path, file_count) or (None, 0)."""
    if not IMAGE_DIR_CUSTOM or not os.path.isdir(IMAGE_DIR_CUSTOM):
        return None, 0

    # Exact folder match only — no prefix matching across types
    folder_path = os.path.join(IMAGE_DIR_CUSTOM, sku)
    if os.path.isdir(folder_path):
        files = [f for f in os.listdir(folder_path)
                 if os.path.isfile(os.path.join(folder_path, f))
                 and not f.startswith('_')
                 and f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
        if files:
            files.sort()
            # Use 2nd photo as thumbnail if available, else 1st
            thumb_idx = 1 if len(files) > 1 else 0
            chosen_file = files[thumb_idx]
            # Prefer the small _thumb_ version if it exists (300px, ~10-20KB)
            thumb_file = f'_thumb_{chosen_file}'
            if os.path.isfile(os.path.join(folder_path, thumb_file)):
                return f'custom/{sku}/{thumb_file}', len(files)
            return f'custom/{sku}/{chosen_file}', len(files)

    return None, 0

def safe_float(val):
    """Parse a value to float, handling commas and empty strings."""
    try:
        return float(str(val).replace(',', '')) if val else 0.0
    except (ValueError, TypeError):
        return 0.0

def parse_product_master_csv(filepath):
    """Parse product_master_active.csv and return dict of {sku: {fields...}}.
    
    Only includes active products (the active CSV already filters these).
    SKU is constructed as '{part_code}_{type}' to match the legacy ZIND format.
    """
    if not os.path.isfile(filepath):
        print(f"ERROR: Product master CSV not found: {filepath}")
        print("       Run the extraction script first:")
        print("       python 'python script/extract_product_master.py'")
        return {}

    items = {}
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            part_code = row.get('sku', '').strip()
            suffix = row.get('type', '').strip()
            if not part_code or not suffix:
                continue

            sku = f"{part_code}_{suffix}"
            items[sku] = {
                'sku': sku,
                'part_code': part_code,
                'suffix': suffix,
                'suffix_label': SUFFIX_MAP.get(suffix, 'Unknown'),
                'name_eng': row.get('name_en', ''),
                'name_thai': row.get('name_th', ''),
                'size': row.get('specification', ''),
                'brand': row.get('brand', ''),
                'qty': int(safe_float(row.get('qty_on_hand', 0))),
                'sale_price': safe_float(row.get('selling_price', 0)),
                'unit_cost': safe_float(row.get('unit_cost', 0)),
                'market_price': safe_float(row.get('market_price', 0)),
                'locations': row.get('warehouse', ''),
            }

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
    # 1. Parse product master CSV (active items only)
    print(f"Reading product master from: {PRODUCT_MASTER_CSV}")
    items = parse_product_master_csv(PRODUCT_MASTER_CSV)

    if not items:
        print("No products found. Aborting.")
        return

    print(f"Found {len(items)} active products to import.")

    # 2. Initialize DB
    conn = init_db()

    # 3. Insert products into the database
    cursor = conn.cursor()
    count = 0
    for sku, item in items.items():
        # Get images — exact SKU match (part_code + suffix)
        thumbnail, image_count = find_thumbnail(sku)

        cursor.execute('''
            INSERT OR REPLACE INTO products (
                sku, part_code, suffix, suffix_label, name_eng, name_thai, size, brand,
                qty, sale_price, unit_cost, market_price, thumbnail, image_count, locations
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            item['sku'], item['part_code'], item['suffix'], item['suffix_label'],
            item['name_eng'], item['name_thai'], item['size'], item['brand'],
            item['qty'], item['sale_price'], item['unit_cost'], item['market_price'],
            thumbnail or '', image_count, item['locations']
        ))
        count += 1
        if count % 2000 == 0:
            conn.commit()
            print(f"  Inserted {count} products...")

    conn.commit()
    conn.close()
    print(f"\nDone! {count} active products loaded.")
    print(f"Database: {DB_FILE}")

if __name__ == '__main__':
    main()
