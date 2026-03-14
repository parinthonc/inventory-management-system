"""
FULL STOCK LEDGER EXTRACTOR v4 (THREADED)
==========================================
CVINDTR1 has TWO sections:

Section 1 - B-tree index (39-byte fixed records):
  doc_ref(8) + category(1) + SKU(20) + location(4) + ptr(6) = 39 bytes

Section 2 - Detail records (0x8A-delimited, ~160-byte padded):
  field[0]  doc_ref       field[1]  category
  field[2]  SKU (20-char) field[3]  item_type
  field[4]  location      field[5-8]  (various)
  field[9]  flag          field[10] qty
  field[11] unit_cost     field[12] unit_price
  field[13] total_cost    field[14] total_price

CVINDMAS field[27] = current qty on hand.
Opening balance = qty_on_hand + total_out - total_in.

Master and balances are keyed by (sku, type) — same SKU with different types
(e.g. 11115-78305-71 type N vs type L) are separate inventory items.
"""

import os, sys, csv, json, time, tempfile, subprocess
from collections import defaultdict
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_CTOTAL = r"Z:\DATA.CTOTAL"
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_SCRIPT_DIR)  # parent of "python script"
OUTPUT_DIR = os.path.join(_PROJECT_DIR, "ledger")

DELIM = 0x8A
REC_LEN = 39

CATEGORIES = {
    '1': ('IN', 'Domestic Purchase'),      # ซื้อในประเทศ
    '2': ('IN', 'Overseas Purchase'),      # ซื้อต่างประเทศ
    '3': ('IN', 'Customer Return'),        # รับคืนจากลูกค้า
    '4': ('IN', 'Other In'),              # อื่นๆ
    '5': ('IN', 'Adjustment In'),          # ปรับปรุง
    'I': ('IN', 'Transfer In'),            # ย้ายเข้า
    '8': ('IN', 'AF'),                     # AF
    '9': ('IN', 'SF'),                     # SF
    'A': ('OUT', 'Sale'),                  # ขาย
    'B': ('OUT', 'Return to Manufacturer'),# คืนผู้ผลิต
    'C': ('OUT', 'Other Out'),             # อื่นๆ
    'D': ('OUT', 'Adjustment Out'),        # ปรับปรุง
    'O': ('OUT', 'Transfer Out'),          # ย้ายออก
    'F': ('OUT', 'Other'),                 # อื่นๆ
}

SKU_TYPES = {'L', 'N', 'G', 'R', 'C', 'F'}

# All confirmed doc prefixes from CVINDTRN scan
DOC_PREFIXES = {
    b'OR', b'IV', b'CN', b'FL', b'FV', b'ST', b'DO', b'FS', b'DN', b'PO', b'RV', b'AD',
    b'CC', b'PC', b'TS', b'CW', b'SI', b'BF', b'HA', b'TH', b'KS', b'YC', b'TL',
    b'CA', b'MH', b'DV', b'YK', b'KP', b'SK', b'UV', b'PT', b'WD', b'AA', b'AC',
    b'TA', b'TC', b'NO', b'CB', b'HS', b'AE', b'HH', b'CS', b'OV', b'CF', b'YD',
    b'BL', b'AS', b'HE', b'HF', b'LE', b'BK', b'LC', b'FB', b'SA', b'TE', b'RR',
    b'H/', b'A0', b'A1', b'A2',
}
DOC_PREFIX_SET = DOC_PREFIXES  # alias

FILE_READ_MAX_RETRIES = 3
FILE_READ_RETRY_BASE_DELAY = 3  # seconds

def _copy_locked_file(filepath):
    """Use Windows 'copy' command to copy a locked file to a temp location.
    The Windows copy command can often read files that Python's open() cannot
    because it uses different file sharing flags internally."""
    tmp_dir = tempfile.mkdtemp(prefix='ledger_')
    tmp_path = os.path.join(tmp_dir, os.path.basename(filepath))
    try:
        result = subprocess.run(
            ['cmd', '/c', 'copy', '/B', filepath, tmp_path],
            capture_output=True, timeout=30
        )
        if result.returncode == 0 and os.path.exists(tmp_path):
            with open(tmp_path, 'rb') as f:
                data = f.read()
            return data
        else:
            err = result.stderr.decode('utf-8', errors='replace').strip()
            print(f"  WARNING: copy command failed for {os.path.basename(filepath)}: {err}")
            return None
    except Exception as e:
        print(f"  WARNING: copy fallback failed for {os.path.basename(filepath)}: {e}")
        return None
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            os.rmdir(tmp_dir)
        except OSError:
            pass


def _read_file_with_retry(filepath):
    """Read a binary file with retry logic for PermissionError (file locked by another process).
    Falls back to Windows copy command if direct reading keeps failing."""
    last_err = None
    for attempt in range(FILE_READ_MAX_RETRIES):
        try:
            with open(filepath, 'rb') as f:
                return f.read()
        except PermissionError as e:
            last_err = e
            delay = FILE_READ_RETRY_BASE_DELAY * (2 ** attempt)
            print(f"  WARNING: {os.path.basename(filepath)} is locked (attempt {attempt+1}/{FILE_READ_MAX_RETRIES}), retrying in {delay}s...")
            time.sleep(delay)

    # All direct-read retries failed — try Windows copy fallback
    print(f"  INFO: Direct read failed after {FILE_READ_MAX_RETRIES} retries. Trying Windows copy fallback for {os.path.basename(filepath)}...")
    data = _copy_locked_file(filepath)
    if data is not None:
        print(f"  OK: Successfully read {os.path.basename(filepath)} via copy fallback ({len(data):,} bytes)")
        return data

    print(f"  ERROR: Cannot read {os.path.basename(filepath)} — both direct read and copy fallback failed.")
    raise last_err


def _safe_float(s):
    try:
        return float(s) if s else 0.0
    except (ValueError, OverflowError):
        return 0.0


def _try_parse_record(data, pos, categories, sku_types):
    """Try to parse a 39-byte B-tree record at pos. Returns dict or None."""
    chunk = data[pos:pos+REC_LEN]
    dr_bytes = chunk[0:8].rstrip(b'\x00')
    if not (dr_bytes and all(0x20 <= b <= 0x7E for b in dr_bytes)):
        return None
    cat_byte = chr(chunk[8]) if chunk[8] < 128 else '?'
    if cat_byte not in categories:
        return None
    sku_bytes = chunk[9:29].rstrip(b'\x00')
    if not sku_bytes or DELIM in sku_bytes:
        return None
    sku = sku_bytes.decode('tis-620', errors='replace').strip()
    if not sku or not any(c.isalnum() for c in sku):
        return None
    doc_ref = chunk[0:8].decode('ascii', errors='replace').strip()
    loc = chunk[29:33].decode('ascii', errors='replace').strip()
    direction, cat_name = categories[cat_byte]
    loc_type = loc[0] if loc and loc[0] in sku_types else ''
    shelf = loc[1:] if loc and len(loc) >= 2 else loc
    return {
        'doc_ref': doc_ref, 'category': cat_byte, 'direction': direction,
        'category_name': cat_name, 'sku': sku, 'sku_type': loc_type, 'shelf': shelf,
    }


def parse_cvindtr1(filepath):
    """Parse CVINDTR1 B-tree — page-structured, 512-byte pages.
    Each page: 7-byte header (byte 0 = record count) + up to 12 x 39-byte records."""
    data = _read_file_with_retry(filepath)

    fsize = len(data)
    records = []
    PAGE_SIZE = 0x200
    PAGE_HEADER = 7
    MAX_PER_PAGE = (PAGE_SIZE - PAGE_HEADER) // REC_LEN  # 12

    for page_off in range(PAGE_SIZE, fsize, PAGE_SIZE):
        if page_off + PAGE_HEADER + REC_LEN > fsize:
            break
        if data[page_off] == 0:
            continue
        rec_count = data[page_off]
        if rec_count > MAX_PER_PAGE:
            rec_count = MAX_PER_PAGE
        for i in range(rec_count):
            pos = page_off + PAGE_HEADER + i * REC_LEN
            if pos + REC_LEN > fsize:
                break
            rec = _try_parse_record(data, pos, CATEGORIES, SKU_TYPES)
            if rec:
                records.append(rec)

    doc_types = defaultdict(int)
    cat_types = defaultdict(int)
    for r in records:
        doc_types[r['doc_ref'][:2]] += 1
        cat_types[r['category']] += 1
    print(f"  CVINDTR1 B-tree: {fsize:,} bytes -> {len(records):,} line items")
    print(f"  Doc types (top 20): {dict(sorted(doc_types.items(), key=lambda x: -x[1])[:20])}")
    print(f"  Categories: {dict(sorted(cat_types.items(), key=lambda x: -x[1]))}")
    return records


def parse_cvindtr1_detail(filepath):
    """Parse 0x8A-delimited detail section using fast find()."""
    data = _read_file_with_retry(filepath)

    fsize = len(data)
    detail_lookup = {}
    record_count = 0
    delim_byte = bytes([DELIM])

    # Use find() to jump between 0x8A delimiters for speed
    pos = 0x200
    while pos < fsize:
        idx = data.find(delim_byte, pos)
        if idx == -1 or idx < 3:
            break

        # Scan backward to find true record start (handles variable-length doc refs)
        scan = idx - 1
        while scan > max(0, idx - 15) and data[scan] != 0 and data[scan] != DELIM:
            scan -= 1
        rec_start = scan + 1 if (data[scan] == 0 or data[scan] == DELIM) else scan
        doc_ref_len = idx - rec_start
        if doc_ref_len < 3 or doc_ref_len > 12:
            pos = idx + 1
            continue

        first_byte = data[rec_start]
        is_prefix = data[rec_start:rec_start+2] in DOC_PREFIX_SET
        is_letter = 0x41 <= first_byte <= 0x5A or 0x61 <= first_byte <= 0x7A
        is_digit = 0x30 <= first_byte <= 0x39
        if not is_prefix and not is_letter and not is_digit:
            pos = idx + 1
            continue
        if not is_prefix:
            dr_bytes = data[rec_start:idx]
            if not all(0x20 <= b <= 0x7E for b in dr_bytes):
                pos = idx + 1
                continue

        rec_end = min(rec_start + 300, fsize)
        fields = data[rec_start:rec_end].split(delim_byte)

        if len(fields) >= 15:
            cat = fields[1].decode('ascii', errors='replace').strip()
            if cat in CATEGORIES:
                sku = fields[2].decode('ascii', errors='replace').strip()
                if sku and any(c.isalnum() for c in sku):
                    doc_ref = fields[0].decode('ascii', errors='replace').strip()
                    qty_str = fields[10].decode('ascii', errors='replace').strip()

                    try:
                        qty = int(float(qty_str)) if qty_str else 1
                    except (ValueError, OverflowError):
                        qty = 1
                    if qty < 1:
                        qty = 1

                    item_type = fields[3].decode('ascii', errors='replace').strip() if len(fields) > 3 else ''
                    key = (doc_ref, sku, item_type)
                    detail_lookup[key] = {
                        'qty': qty,
                        'unit_cost': _safe_float(fields[11].decode('ascii', errors='replace').strip()),
                        'unit_price': _safe_float(fields[12].decode('ascii', errors='replace').strip()),
                        'total_cost': _safe_float(fields[13].decode('ascii', errors='replace').strip()),
                        'total_price': _safe_float(fields[14].decode('ascii', errors='replace').strip()),
                    }
                    record_count += 1

                    # Jump past this record (~160 bytes null-padded)
                    skip = rec_start + 100
                    while skip < fsize and data[skip] != 0:
                        skip += 1
                    while skip < fsize and data[skip] == 0:
                        skip += 1
                    pos = skip
                    continue

        pos = idx + 1

    qty_dist = defaultdict(int)
    for v in detail_lookup.values():
        qty_dist[v['qty']] += 1
    top_qtys = sorted(qty_dist.items(), key=lambda x: -x[1])[:15]
    print(f"  CVINDTR1 detail: {record_count:,} records with qty/price")
    print(f"  Qty distribution (top 15): {dict(top_qtys)}")
    return detail_lookup


def parse_cvindtrn(filepath):
    """Parse CVINDTRN - 0x8A-delimited transaction headers."""
    data = _read_file_with_retry(filepath)

    fsize = len(data)
    doc_headers = {}
    delim_byte = bytes([DELIM])

    pos = 0
    while pos < fsize - 30:
        b = data[pos]
        is_letter = 0x41 <= b <= 0x5A or 0x61 <= b <= 0x7A
        is_digit = 0x30 <= b <= 0x39
        if is_letter or is_digit:
            if not is_letter:
                dr_bytes = data[pos:pos+8].rstrip(b'\x00')
                if not (dr_bytes and all(0x20 <= b <= 0x7E for b in dr_bytes)):
                    pos += 1
                    continue
            # Find 0x8A within next 12 bytes
            delim_idx = data.find(delim_byte, pos + 2, pos + 13)
            if delim_idx != -1:
                rec_end = min(pos + 400, fsize)
                fields = data[pos:rec_end].split(delim_byte)

                if len(fields) >= 4:
                    cat = fields[1].decode('ascii', errors='replace').strip()
                    date_str = fields[2].decode('ascii', errors='replace').strip()

                    if len(date_str) == 8 and '/' in date_str and cat in CATEGORIES:
                        doc_ref = fields[0].decode('ascii', errors='replace').strip()
                        from_to = fields[3].decode('ascii', errors='replace').strip()

                        try:
                            parts = date_str.split('/')
                            dd, mm, yy = int(parts[0]), int(parts[1]), int(parts[2])
                            greg_year = 1957 + yy if yy < 100 else yy - 543
                            formatted_date = datetime(greg_year, mm, dd).strftime('%Y-%m-%d')
                        except Exception:
                            formatted_date = date_str

                        direction, cat_name = CATEGORIES.get(cat, ('UNK', 'Unknown'))

                        doc_headers[doc_ref] = {
                            'date': formatted_date,
                            'date_raw': date_str,
                            'category': cat,
                            'direction': direction,
                            'category_name': cat_name,
                            'from_to': from_to,
                        }
                        pos += len(fields[0]) + sum(len(f) + 1 for f in fields[1:4])
                        continue
        pos += 1

    print(f"  CVINDTRN: {fsize:,} bytes -> {len(doc_headers):,} document headers")
    return doc_headers


def parse_cvindmas(filepath):
    """Parse CVINDMAS for SKU master data including qty_on_hand (field[27])."""
    data = _read_file_with_retry(filepath)

    fsize = len(data)
    sku_master = {}

    pos = 0x200
    while pos < fsize - 100:
        b = data[pos]
        if b == 0 or b == 0x20:
            pos += 1
            continue

        chunk = data[pos:pos+30]
        delim_pos = chunk.find(bytes([DELIM]))

        if 5 <= delim_pos <= 25:
            potential_sku = chunk[:delim_pos].decode('ascii', errors='replace').strip()
            if len(potential_sku) >= 2 and all(c >= ' ' and c < '\x7f' for c in potential_sku):
                rec_end = pos + delim_pos
                for i in range(pos + delim_pos, min(pos + 800, fsize - 4)):
                    if data[i:i+4] == b'\x00\x00\x00\x00':
                        rec_end = i
                        break

                fields = data[pos:rec_end].split(bytes([DELIM]))

                if len(fields) >= 15:
                    sku = fields[0].decode('ascii', errors='replace').strip()
                    item_type = fields[1].decode('ascii', errors='replace').strip() if len(fields) > 1 else ''
                    name_en = fields[3].decode('ascii', errors='replace').strip() if len(fields) > 3 else ''
                    uom = fields[5].decode('ascii', errors='replace').strip() if len(fields) > 5 else ''

                    qty_on_hand = 0
                    if len(fields) > 27:
                        qoh_str = fields[27].decode('ascii', errors='replace').strip()
                        try:
                            qty_on_hand = int(float(qoh_str)) if qoh_str else 0
                        except (ValueError, OverflowError):
                            qty_on_hand = 0

                    if len(item_type) == 1 and item_type.isalpha():
                        sku_master[(sku, item_type)] = {
                            'sku': sku,
                            'type': item_type,
                            'name_en': name_en,
                            'uom': uom,
                            'qty_on_hand': qty_on_hand,
                        }
                        pos = rec_end
                        continue

        pos += 1

    print(f"  CVINDMAS: {fsize:,} bytes -> {len(sku_master):,} SKU master records (keyed by sku+type)")
    return sku_master


def _ensure_network_drive(path):
    """Wake up a mapped network drive that Windows may have silently disconnected.
    Windows drops idle network drive connections after ~15 min. Accessing the drive
    in File Explorer reconnects it; this function does the same thing programmatically."""
    drive = os.path.splitdrive(path)[0]  # e.g. "Z:"
    if not drive:
        return True

    # Step 1: Try listing the directory (triggers Windows to reconnect)
    try:
        os.listdir(drive + '\\')
        print(f"  Network drive {drive} is accessible")
        return True
    except (PermissionError, OSError):
        pass

    # Step 2: Force reconnect via 'net use'
    print(f"  WARNING: {drive} appears disconnected, attempting reconnect...")
    try:
        result = subprocess.run(
            ['net', 'use', drive],
            capture_output=True, timeout=15
        )
        # After net use, try listing again
        os.listdir(drive + '\\')
        print(f"  OK: {drive} reconnected successfully")
        return True
    except Exception as e:
        print(f"  ERROR: Could not reconnect {drive}: {e}")
        return False


if __name__ == '__main__':
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    t_start = time.time()

    print("=" * 80)
    print("FULL STOCK LEDGER EXTRACTION v4 (THREADED)")
    print("=" * 80)

    # Wake up network drive before accessing files
    if not _ensure_network_drive(BASE_CTOTAL):
        print("  FATAL: Cannot access network drive. Exiting.")
        sys.exit(1)

    cvindtr1_path = os.path.join(BASE_CTOTAL, "CVINDTR1")
    cvindtrn_path = os.path.join(BASE_CTOTAL, "CVINDTRN")
    cvindmas_path = os.path.join(BASE_CTOTAL, "CVINDMAS")

    print("\n[PARALLEL] Parsing all data sources with 4 threads...")
    results = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(parse_cvindtr1, cvindtr1_path): 'btree',
            executor.submit(parse_cvindtr1_detail, cvindtr1_path): 'detail',
            executor.submit(parse_cvindtrn, cvindtrn_path): 'headers',
            executor.submit(parse_cvindmas, cvindmas_path): 'master',
        }
        for future in as_completed(futures):
            label = futures[future]
            results[label] = future.result()

    line_items = results['btree']
    detail_lookup = results['detail']
    doc_headers = results['headers']
    sku_master = results['master']

    t_parse = time.time()
    print(f"\n  Parsing done in {t_parse - t_start:.1f}s")

    # Join — use loc_type from B-tree as primary type, master keyed by (sku, type)
    print("\n" + "=" * 80)
    print("JOINING DATA")
    print("=" * 80)

    seen_keys = set()
    dedup_items = []
    for item in line_items:
        key = (item['doc_ref'], item['sku'], item.get('sku_type', ''))
        if key in seen_keys:
            continue
        seen_keys.add(key)
        dedup_items.append(item)
    dedup_count = len(line_items) - len(dedup_items)
    if dedup_count:
        print(f"  Deduplicated: {dedup_count} multi-shelf duplicates removed")

    ledger = []
    matched_headers = 0
    unmatched_headers = 0
    matched_detail = 0
    unmatched_detail = 0

    for item in dedup_items:
        doc_ref = item['doc_ref']
        sku = item['sku']
        loc_type = item.get('sku_type', '')
        header = doc_headers.get(doc_ref)

        master = sku_master.get((sku, loc_type), {})
        if not master:
            for t in SKU_TYPES:
                master = sku_master.get((sku, t), {})
                if master:
                    break

        sku_type = loc_type if loc_type else master.get('type', '')

        detail = detail_lookup.get((doc_ref, sku, sku_type))
        if not detail:
            detail = detail_lookup.get((doc_ref, sku, ''))
            if not detail:
                for t in SKU_TYPES:
                    detail = detail_lookup.get((doc_ref, sku, t))
                    if detail:
                        break

        direction = item['direction']
        qty = detail['qty'] if detail else 1
        qty_in = qty if direction == 'IN' else 0
        qty_out = qty if direction == 'OUT' else 0

        entry = {
            'date': header['date'] if header else '',
            'doc_ref': doc_ref,
            'doc_type': doc_ref[:2],
            'category': item['category'],
            'direction': direction,
            'category_name': item['category_name'],
            'from_to': header['from_to'] if header else '',
            'sku': sku,
            'sku_type': sku_type,
            'name_en': master.get('name_en', ''),
            'uom': master.get('uom', ''),
            'shelf': item.get('shelf', ''),
            'qty_in': qty_in,
            'qty_out': qty_out,
            'unit_cost': detail['unit_cost'] if detail else 0.0,
            'unit_price': detail['unit_price'] if detail else 0.0,
        }
        ledger.append(entry)

        if header:
            matched_headers += 1
        else:
            unmatched_headers += 1
        if detail:
            matched_detail += 1
        else:
            unmatched_detail += 1

    print(f"  Matched headers: {matched_headers:,}  Unmatched: {unmatched_headers:,}")
    print(f"  Matched detail: {matched_detail:,}  Unmatched: {unmatched_detail:,}")
    print(f"  Total entries: {len(ledger):,}")

    # Sort by (sku, type, date, doc_ref) — separate balances per type
    ledger_sorted = sorted(ledger, key=lambda x: (x['sku'], x['sku_type'], x['date'] or '9999', x['doc_ref']))

    net_by_key = defaultdict(lambda: {'in': 0, 'out': 0})
    for entry in ledger_sorted:
        key = (entry['sku'], entry['sku_type'])
        net_by_key[key]['in'] += entry['qty_in']
        net_by_key[key]['out'] += entry['qty_out']

    opening_balance = {}
    for (sku, typ), mov in net_by_key.items():
        current_qty = sku_master.get((sku, typ), {}).get('qty_on_hand', 0)
        opening_balance[(sku, typ)] = current_qty + mov['out'] - mov['in']

    for (sku, typ), md in sku_master.items():
        if (sku, typ) not in opening_balance:
            opening_balance[(sku, typ)] = md.get('qty_on_hand', 0)

    ob_pos = sum(1 for v in opening_balance.values() if v > 0)
    ob_zero = sum(1 for v in opening_balance.values() if v == 0)
    ob_neg = sum(1 for v in opening_balance.values() if v < 0)
    print(f"  Opening balances: {len(opening_balance):,} (sku, type) pairs "
          f"(pos: {ob_pos:,}, zero: {ob_zero:,}, neg: {ob_neg:,})")

    opening_rows = []
    for (sku, typ) in sorted(opening_balance.keys()):
        ob = opening_balance[(sku, typ)]
        if ob == 0:
            continue
        master = sku_master.get((sku, typ), {})
        opening_rows.append({
            'date': '2014-01-01', 'doc_ref': 'OPENING', 'doc_type': 'OB',
            'category': '', 'direction': 'OPENING', 'category_name': 'Opening Balance',
            'from_to': '', 'sku': sku, 'sku_type': typ,
            'name_en': master.get('name_en', ''), 'uom': master.get('uom', ''),
            'shelf': '', 'qty_in': ob if ob > 0 else 0,
            'qty_out': abs(ob) if ob < 0 else 0,
            'unit_cost': 0.0, 'unit_price': 0.0,
        })

    ledger_sorted = opening_rows + ledger_sorted
    ledger_sorted.sort(key=lambda x: (x['sku'], x['sku_type'], x['date'] or '9999', x['doc_ref']))

    balance_by_key = {}
    for entry in ledger_sorted:
        key = (entry['sku'], entry['sku_type'])
        bal = balance_by_key.get(key, 0)
        bal += entry['qty_in'] - entry['qty_out']
        balance_by_key[key] = bal
        entry['running_balance'] = bal
    total_in = sum(e['qty_in'] for e in ledger_sorted)
    total_out = sum(e['qty_out'] for e in ledger_sorted)
    print(f"  Opening rows: {len(opening_rows):,}")
    print(f"  Total in: {total_in:,}  out: {total_out:,}  rows: {len(ledger_sorted):,}")

    # Validate
    print("\n" + "=" * 80)
    print("VALIDATION")
    print("=" * 80)

    def show(label, entries, limit=15):
        print(f"\n  {label}: {len(entries)} entries (first {limit})")
        for e in entries[:limit]:
            print(f"    {e['date']}  {e['doc_ref']:<10s} {e['category_name']:<22s} "
                  f"in={e['qty_in']:<5} out={e['qty_out']:<5} bal={e['running_balance']}  type={e['sku_type']}")

    show("91375-43100 N (opening=9)", [e for e in ledger_sorted if e['sku'] == '91375-43100' and e['sku_type'] == 'N'])
    show("9138744-01 L (opening=10)", [e for e in ledger_sorted if e['sku'] == '9138744-01' and e['sku_type'] == 'L'])
    show("91351-05300 L (IV575580 qty=2)", [e for e in ledger_sorted if e['sku'] == '91351-05300' and e['sku_type'] == 'L'])
    show("91402-01100 R (opening=2, CC220715)", [e for e in ledger_sorted if e['sku'] == '91402-01100' and e['sku_type'] == 'R'])
    show("91433-10701 L (opening=46, 018-0867)", [e for e in ledger_sorted if e['sku'] == '91433-10701' and e['sku_type'] == 'L'])
    show("11115-78305-71 N (should exist!)", [e for e in ledger_sorted if e['sku'] == '11115-78305-71' and e['sku_type'] == 'N'])

    # Write outputs
    print("\n" + "=" * 80)
    print("WRITING OUTPUTS")
    print("=" * 80)

    csv_path = os.path.join(OUTPUT_DIR, "stock_ledger_full.csv.new")
    fieldnames = ['date', 'doc_ref', 'doc_type', 'category', 'direction', 'category_name',
                  'from_to', 'sku', 'sku_type', 'name_en', 'uom', 'shelf',
                  'qty_in', 'qty_out', 'running_balance', 'unit_cost', 'unit_price']
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(ledger_sorted)
    print(f"  stock_ledger_full.csv.new: {len(ledger_sorted):,} rows")

    master_path = os.path.join(OUTPUT_DIR, "sku_master.csv")
    master_fields = ['sku', 'type', 'name_en', 'uom', 'qty_on_hand', 'opening_balance']
    with open(master_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=master_fields)
        writer.writeheader()
        for (sku, typ) in sorted(sku_master.keys()):
            row = {k: sku_master[(sku, typ)].get(k, '') for k in master_fields}
            row['opening_balance'] = opening_balance.get((sku, typ), 0)
            writer.writerow(row)
    print(f"  sku_master.csv: {len(sku_master):,} (sku, type) entries")

    cat_counts = defaultdict(int)
    doc_counts = defaultdict(int)
    for e in ledger:
        cat_counts[f"{e['category']} ({e['category_name']})"] += 1
        doc_counts[e['doc_type']] += 1

    stats = {
        'version': 'v4-threaded',
        'timestamp': datetime.now().isoformat(),
        'source': 'DATA.CTOTAL',
        'total_entries': len(ledger),
        'matched_headers': matched_headers,
        'unmatched_headers': unmatched_headers,
        'matched_detail_qty': matched_detail,
        'unmatched_detail_qty': unmatched_detail,
        'total_qty_in': total_in,
        'total_qty_out': total_out,
        'unique_skus': len(set((e['sku'], e['sku_type']) for e in ledger)),
        'unique_documents': len(set(e['doc_ref'] for e in ledger)),
        'sku_master_count': len(sku_master),
        'date_range': {
            'earliest': min((e['date'] for e in ledger if e['date']), default=''),
            'latest': max((e['date'] for e in ledger if e['date']), default=''),
        },
        'category_breakdown': dict(sorted(cat_counts.items(), key=lambda x: -x[1])),
        'doc_type_breakdown': dict(sorted(doc_counts.items(), key=lambda x: -x[1])),
    }
    with open(os.path.join(OUTPUT_DIR, "extraction_stats_v4.json"), 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f"  extraction_stats_v4.json")

    t_end = time.time()
    print(f"\n{'=' * 80}")
    print(f"DONE! Total: {t_end - t_start:.1f}s (parse: {t_parse - t_start:.1f}s)")
    print(f"{'=' * 80}")
