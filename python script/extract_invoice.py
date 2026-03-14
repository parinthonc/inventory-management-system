"""
Invoice Detail Extractor
========================
Extracts invoice headers and line items from the legacy ERP binary files.

Sources:
  - DATA.CW/CVIVDMAS  (118 MB) → Invoice headers (37 0x8A-delimited fields)
  - DATA.CW/CVIVDTRN  (87 MB)  → Invoice line items (21 0x8A-delimited fields)

Invoice types:
  - IV prefix = VAT invoice (ใบกำกับภาษี)
  - OR prefix = Off-the-book transaction (no VAT)

Each line-item record links the IV doc_ref to its corresponding OR doc_ref.

Outputs:
  - invoice_headers.csv   — One row per invoice (date, customer, amounts, VAT)
  - invoice_line_items.csv — One row per line item (SKU, qty, price, IV↔OR link)
  - invoice_stats.json     — Extraction metadata and validation results
"""

import csv, os, sys, json, time, re
from collections import defaultdict
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_CW = r"Z:\DATA.CW"
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_SCRIPT_DIR)  # parent of "python script"
OUTPUT_DIR = os.path.join(_PROJECT_DIR, "invoice")

DELIM = 0x8A

# ── Custom ERP Thai encoding → TIS-620 byte mapping ────────────────────────
# Same mapping used across all extraction scripts (product master, customer master).
THAI_BYTE_MAP = {
    0xA1: 0xA1,  # ก -> ก
    0xA2: 0xA2,  # ข -> ข
    0xA3: 0xA4,  # ฃ -> ค
    0xA4: 0xA6,  # ฆ -> ฆ
    0xA5: 0xA7,  # ฅ -> ง
    0xA6: 0xA8,  # ฆ -> จ
    0xA7: 0xA9,  # ง -> ฉ
    0xA8: 0xAA,  # จ -> ช
    0xA9: 0xAB,  # ฉ -> ซ
    0xAA: 0xAC,  # ช -> ฌ
    0xAB: 0xAD,  # ซ -> ญ
    0xAE: 0xB0,  # ฎ -> ฐ
    0xB1: 0xB3,  # ฑ -> ณ
    0xB2: 0xB4,  # ฒ -> ด
    0xB3: 0xB5,  # ณ -> ต
    0xB4: 0xB6,  # ด -> ถ
    0xB5: 0xB7,  # ต -> ท
    0xB6: 0xB8,  # ถ -> ธ
    0xB7: 0xB9,  # ท -> น
    0xB8: 0xBA,  # ธ -> บ
    0xB9: 0xBB,  # น -> ป
    0xBA: 0xBC,  # บ -> ผ
    0xBB: 0xBD,  # ป -> ฝ
    0xBC: 0xBE,  # ผ -> พ
    0xBD: 0xBF,  # ฝ -> ฟ
    0xBF: 0xC1,  # ฟ -> ม
    0xC0: 0xC2,  # ภ -> ย
    0xC1: 0xC3,  # ม -> ร
    0xC3: 0xC5,  # ร -> ล
    0xC4: 0xC7,  # ฤ -> ว
    0xC5: 0xC8,  # ล -> ศ
    0xC6: 0xC9,  # ฦ -> ษ
    0xC7: 0xCA,  # ว -> ส
    0xC8: 0xCB,  # ศ -> ห
    0xCA: 0xCD,  # ส -> อ
    0xCB: 0xCE,  # ห -> ฮ
    0xCC: 0xD0,  # ฬ -> ะ
    0xCE: 0xD2,  # ฮ -> า
    0xCF: 0xD3,  # ฯ -> ำ
    0xD0: 0xE0,  # ะ -> เ
    0xD1: 0xE1,  # ั -> แ
    0xD2: 0xE2,  # า -> โ
    0xD3: 0xE3,  # ำ -> ใ
    0xD4: 0xE4,  # ิ -> ไ
    0xD6: 0xCF,  # ึ -> ฯ
    0xD7: 0xD8,  # ื -> ุ
    0xD8: 0xD9,  # ุ -> ู
    0xD9: 0xD4,  # ู -> ิ
    0xDA: 0xD5,  # ฺ -> ี
    0xDB: 0xD6,  # → ึ
    0xDC: 0xD7,  # → ื
    0xDD: 0xD1,  # → ั
    0xDE: 0xED,  # → ํ
    0xDF: 0xE7,  # ฿ -> ็
    0xE0: 0xE8,  # เ -> ่
    0xE1: 0xE9,  # แ -> ้
    0xE2: 0xEA,  # โ -> ๊
    0xE3: 0xEB,  # ใ -> ๋
    0xE4: 0xEC,  # ไ -> ์
}

# ── Expected field counts for defensive validation ──────────────────────────
EXPECTED_HEADER_FIELDS = 37   # CVIVDMAS detail records
EXPECTED_LINE_ITEM_FIELDS = 21  # CVIVDTRN detail records


# ── Helper functions ────────────────────────────────────────────────────────

def decode_thai(raw_bytes):
    """Decode raw bytes from ERP custom Thai encoding to proper Thai text."""
    mapped = bytearray()
    for b in raw_bytes:
        if b >= 0xA0 and b in THAI_BYTE_MAP:
            mapped.append(THAI_BYTE_MAP[b])
        else:
            mapped.append(b)
    return bytes(mapped).decode('tis-620', errors='replace').strip()


def convert_be_date(date_str):
    """Convert DD/MM/YY Buddhist Era date to YYYY-MM-DD Gregorian."""
    if not date_str or '/' not in date_str or date_str.strip() in ('', '/  /', '/ /', '  /  /  '):
        return ''
    parts = date_str.strip().split('/')
    if len(parts) != 3:
        return date_str
    try:
        dd, mm, yy = parts[0].strip(), parts[1].strip(), parts[2].strip()
        if not dd or not mm or not yy:
            return ''
        dd, mm, yy = int(dd), int(mm), int(yy)
        if yy < 100:
            yyyy_be = yy + 2500
        else:
            yyyy_be = yy
        yyyy_ad = yyyy_be - 543
        if yyyy_ad < 1900 or yyyy_ad > 2100 or mm < 1 or mm > 12 or dd < 1 or dd > 31:
            return date_str
        return f"{yyyy_ad:04d}-{mm:02d}-{dd:02d}"
    except (ValueError, IndexError):
        return date_str


def safe_float(val):
    """Safely convert a string to float, returning 0.0 on failure."""
    if not val or not val.strip():
        return 0.0
    try:
        return float(val.strip().replace(',', ''))
    except (ValueError, OverflowError):
        return 0.0


def safe_int(val):
    """Safely convert a string to int, returning 0 on failure."""
    if not val or not val.strip():
        return 0
    try:
        return int(float(val.strip().replace(',', '')))
    except (ValueError, OverflowError):
        return 0


# ── CVIVDMAS Parser — Invoice Headers ──────────────────────────────────────

def parse_cvivdmas(filepath):
    """Parse CVIVDMAS (invoice master) 0x8A-delimited detail section.

    Returns a dict keyed by invoice_number -> header record.
    """
    with open(filepath, 'rb') as f:
        data = f.read()

    fsize = len(data)
    headers = {}
    field_counts = []
    delim_byte = bytes([DELIM])

    pos = 0x200  # Skip 512-byte file header

    while pos < fsize - 30:
        b = data[pos]

        # Skip nulls and spaces
        if b == 0 or b == 0x20:
            pos += 1
            continue

        # Look for IV or OR prefix followed by digit
        is_iv = (b == 0x49 and pos + 2 < fsize and data[pos+1] == 0x56
                 and 0x30 <= data[pos+2] <= 0x39)
        is_or = (b == 0x4F and pos + 2 < fsize and data[pos+1] == 0x52
                 and 0x30 <= data[pos+2] <= 0x39)

        if not (is_iv or is_or):
            pos += 1
            continue

        # Check for 0x8A delimiter within 12 bytes (doc_ref field end)
        delim_idx = data.find(delim_byte, pos + 3, pos + 12)
        if delim_idx == -1:
            pos += 1
            continue

        # Find record end (4 consecutive null bytes), search up to 2000 bytes
        rec_end = min(pos + 2000, fsize)
        for i in range(pos + 10, min(rec_end, fsize - 3)):
            if data[i:i+4] == b'\x00\x00\x00\x00':
                rec_end = i
                break

        fields = data[pos:rec_end].split(delim_byte)

        # Valid header records have ~37 fields with a date in field[2]
        if len(fields) >= 20:
            doc_ref = fields[0].decode('ascii', errors='replace').strip().rstrip('\x00')

            # Reject B-tree index entries that are misread as delimited records:
            # valid doc_refs are purely printable ASCII (letters, digits, hyphens)
            if not doc_ref or not all(0x20 <= ord(c) <= 0x7E for c in doc_ref):
                pos += 1
                continue

            doc_type = fields[1].decode('ascii', errors='replace').strip() if len(fields) > 1 else ''

            # Validate: field[2] should look like a date DD/MM/YY
            date_raw = fields[2].decode('ascii', errors='replace').strip() if len(fields) > 2 else ''
            if '/' not in date_raw or len(date_raw) < 6:
                pos += 1
                continue

            field_counts.append(len(fields))

            # Extract header fields
            rec = {
                'invoice_number': doc_ref,
                'doc_type': doc_type,
                'invoice_date_raw': date_raw,
                'invoice_date': convert_be_date(date_raw),
            }

            # Due date
            if len(fields) > 3:
                due_raw = fields[3].decode('ascii', errors='replace').strip()
                rec['due_date_raw'] = due_raw
                rec['due_date'] = convert_be_date(due_raw)
            else:
                rec['due_date_raw'] = ''
                rec['due_date'] = ''

            # Customer code
            if len(fields) > 4:
                rec['customer_code'] = fields[4].decode('ascii', errors='replace').strip()
            else:
                rec['customer_code'] = ''

            # Customer name (Thai encoded, ~60 bytes)
            if len(fields) > 5:
                rec['customer_name'] = decode_thai(fields[5])
            else:
                rec['customer_name'] = ''

            # Salesperson code
            if len(fields) > 6:
                rec['salesperson_code'] = fields[6].decode('ascii', errors='replace').strip()
            else:
                rec['salesperson_code'] = ''

            # Cancel/void date field[8]
            if len(fields) > 8:
                void_raw = fields[8].decode('ascii', errors='replace').strip()
                rec['void_date'] = convert_be_date(void_raw)
            else:
                rec['void_date'] = ''

            # Payment type field[9]
            if len(fields) > 9:
                rec['payment_type'] = fields[9].decode('ascii', errors='replace').strip()
            else:
                rec['payment_type'] = ''

            # Delivery address (Thai encoded, ~105 bytes) field[10]
            if len(fields) > 10:
                rec['delivery_address'] = decode_thai(fields[10])
            else:
                rec['delivery_address'] = ''

            # Credit term code field[15]
            if len(fields) > 15:
                rec['credit_term_code'] = fields[15].decode('ascii', errors='replace').strip()
            else:
                rec['credit_term_code'] = ''

            # Invoice type field[17]
            if len(fields) > 17:
                rec['invoice_type'] = fields[17].decode('ascii', errors='replace').strip()
            else:
                rec['invoice_type'] = ''

            # Credit days field[20]
            if len(fields) > 20:
                rec['credit_days'] = safe_int(fields[20].decode('ascii', errors='replace').strip())
            else:
                rec['credit_days'] = 0

            # Subtotal field[23]
            if len(fields) > 23:
                rec['subtotal'] = safe_float(fields[23].decode('ascii', errors='replace').strip())
            else:
                rec['subtotal'] = 0.0

            # Net amount field[24]
            if len(fields) > 24:
                rec['net_amount'] = safe_float(fields[24].decode('ascii', errors='replace').strip())
            else:
                rec['net_amount'] = 0.0

            # VAT rate field[25]
            if len(fields) > 25:
                rec['vat_rate'] = safe_float(fields[25].decode('ascii', errors='replace').strip())
            else:
                rec['vat_rate'] = 0.0

            # VAT amount field[26]
            if len(fields) > 26:
                rec['vat_amount'] = safe_float(fields[26].decode('ascii', errors='replace').strip())
            else:
                rec['vat_amount'] = 0.0

            # Grand total field[27]
            if len(fields) > 27:
                rec['grand_total'] = safe_float(fields[27].decode('ascii', errors='replace').strip())
            else:
                rec['grand_total'] = 0.0

            # Discount field[28] (observed as ".5" or "0")
            if len(fields) > 28:
                rec['discount'] = safe_float(fields[28].decode('ascii', errors='replace').strip())
            else:
                rec['discount'] = 0.0

            # Creation timestamp field[32]
            if len(fields) > 32:
                ts_raw = fields[32].decode('ascii', errors='replace').strip()
                # Format: "DD/MM/YYHH:MM:SS" — split date and time
                if len(ts_raw) >= 16 and '/' in ts_raw and ':' in ts_raw:
                    date_part = ts_raw[:8]
                    time_part = ts_raw[8:]
                    rec['created_date'] = convert_be_date(date_part)
                    rec['created_time'] = time_part
                else:
                    rec['created_date'] = ''
                    rec['created_time'] = ''
            else:
                rec['created_date'] = ''
                rec['created_time'] = ''

            # Tax ID field[33]
            if len(fields) > 33:
                rec['tax_id'] = fields[33].decode('ascii', errors='replace').strip()
            else:
                rec['tax_id'] = ''

            headers[doc_ref] = rec
            pos = rec_end + 1
            continue

        pos += 1

    print(f"  CVIVDMAS: {fsize:,} bytes → {len(headers):,} invoice headers")
    return headers, field_counts


# ── CVIVDTRN Parser — Invoice Line Items ───────────────────────────────────

def parse_cvivdtrn(filepath):
    """Parse CVIVDTRN 0x8A-delimited detail section for invoice line items.

    Returns a list of line-item records.
    """
    with open(filepath, 'rb') as f:
        data = f.read()

    fsize = len(data)
    line_items = []
    field_counts = []
    delim_byte = bytes([DELIM])

    pos = 0x200  # Skip file header

    while pos < fsize - 30:
        b = data[pos]

        # Skip nulls and spaces
        if b == 0 or b == 0x20:
            pos += 1
            continue

        # Look for IV or OR prefix followed by digit
        is_iv = (b == 0x49 and pos + 2 < fsize and data[pos+1] == 0x56
                 and 0x30 <= data[pos+2] <= 0x39)
        is_or = (b == 0x4F and pos + 2 < fsize and data[pos+1] == 0x52
                 and 0x30 <= data[pos+2] <= 0x39)

        if not (is_iv or is_or):
            pos += 1
            continue

        # Check for 0x8A delimiter within 12 bytes
        delim_idx = data.find(delim_byte, pos + 3, pos + 12)
        if delim_idx == -1:
            pos += 1
            continue

        # Find record end
        rec_end = min(pos + 2000, fsize)
        for i in range(pos + 10, min(rec_end, fsize - 3)):
            if data[i:i+4] == b'\x00\x00\x00\x00':
                rec_end = i
                break

        fields = data[pos:rec_end].split(delim_byte)

        # Valid line-item records have ~21 fields with a SKU in field[1] (20 chars)
        if len(fields) >= 15:
            iv_doc_ref = fields[0].decode('ascii', errors='replace').strip().rstrip('\x00')

            # Reject non-printable doc refs (B-tree artifacts)
            if not iv_doc_ref or not all(0x20 <= ord(c) <= 0x7E for c in iv_doc_ref):
                pos += 1
                continue

            # field[1] is the SKU (20-char padded)
            sku_raw = fields[1].decode('ascii', errors='replace').strip() if len(fields) > 1 else ''

            # Validate: field[1] should look like an SKU, not a date or another doc ref
            # SKU codes contain alphanumeric + hyphens (e.g. "37B-1CJ-5010R", "32670-12620-71")
            if not sku_raw or len(sku_raw) < 2:
                pos += 1
                continue

            # Check field[2] should be a single-character type (R, G, L, N, etc.)
            sku_type = fields[2].decode('ascii', errors='replace').strip() if len(fields) > 2 else ''
            if len(sku_type) != 1 or not sku_type.isalpha():
                pos += 1
                continue

            field_counts.append(len(fields))

            rec = {
                'iv_doc_ref': iv_doc_ref,
                'sku': sku_raw,
                'sku_type': sku_type,
            }

            # Location code field[3]
            if len(fields) > 3:
                rec['location'] = fields[3].decode('ascii', errors='replace').strip()
            else:
                rec['location'] = ''

            # Product name (Thai encoded) field[4]
            if len(fields) > 4:
                rec['product_name'] = decode_thai(fields[4])
            else:
                rec['product_name'] = ''

            # OR doc_ref field[5]
            if len(fields) > 5:
                rec['or_doc_ref'] = fields[5].decode('ascii', errors='replace').strip()
            else:
                rec['or_doc_ref'] = ''

            # Salesperson name (Thai) field[6]
            if len(fields) > 6:
                rec['salesperson_name'] = decode_thai(fields[6])
            else:
                rec['salesperson_name'] = ''

            # Quantity field[10]
            if len(fields) > 10:
                rec['qty'] = safe_int(fields[10].decode('ascii', errors='replace').strip())
            else:
                rec['qty'] = 0

            # Unit cost field[11]
            if len(fields) > 11:
                rec['unit_cost'] = safe_float(fields[11].decode('ascii', errors='replace').strip())
            else:
                rec['unit_cost'] = 0.0

            # Unit price field[12]
            if len(fields) > 12:
                rec['unit_price'] = safe_float(fields[12].decode('ascii', errors='replace').strip())
            else:
                rec['unit_price'] = 0.0

            # Total cost field[13]
            if len(fields) > 13:
                rec['total_cost'] = safe_float(fields[13].decode('ascii', errors='replace').strip())
            else:
                rec['total_cost'] = 0.0

            # Total price field[14]
            if len(fields) > 14:
                rec['total_price'] = safe_float(fields[14].decode('ascii', errors='replace').strip())
            else:
                rec['total_price'] = 0.0

            # Line number field[19]
            if len(fields) > 19:
                rec['line_number'] = safe_int(fields[19].decode('ascii', errors='replace').strip())
            else:
                rec['line_number'] = 0

            line_items.append(rec)
            pos = rec_end + 1
            continue

        pos += 1

    print(f"  CVIVDTRN: {fsize:,} bytes → {len(line_items):,} invoice line items")
    return line_items, field_counts


# ── Main ────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    t_start = time.time()

    print("=" * 80)
    print("INVOICE DETAIL EXTRACTION")
    print("Source: DATA.CW/CVIVDMAS + CVIVDTRN")
    print("=" * 80)

    cvivdmas_path = os.path.join(BASE_CW, "CVIVDMAS")
    cvivdtrn_path = os.path.join(BASE_CW, "CVIVDTRN")

    # ── 1. Parse both files in parallel ─────────────────────────────────────
    print("\n[PARALLEL] Parsing CVIVDMAS + CVIVDTRN with 2 threads...")
    results = {}
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(parse_cvivdmas, cvivdmas_path): 'headers',
            executor.submit(parse_cvivdtrn, cvivdtrn_path): 'line_items',
        }
        for future in as_completed(futures):
            label = futures[future]
            results[label] = future.result()

    headers, header_field_counts = results['headers']
    line_items, line_item_field_counts = results['line_items']

    t_parse = time.time()
    print(f"\n  Parsing done in {t_parse - t_start:.1f}s")

    # ── 2. Summary statistics ───────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    # Header stats
    iv_headers = sum(1 for h in headers.values() if h['doc_type'] == 'IV')
    or_headers = sum(1 for h in headers.values() if h['doc_type'] == 'OR')
    other_headers = len(headers) - iv_headers - or_headers
    print(f"\n  Invoice headers: {len(headers):,}")
    print(f"    IV (VAT invoice): {iv_headers:,}")
    print(f"    OR (off-book):    {or_headers:,}")
    if other_headers:
        print(f"    Other:            {other_headers:,}")

    # Date range
    dates = [h['invoice_date'] for h in headers.values() if h['invoice_date']]
    if dates:
        print(f"    Date range: {min(dates)} to {max(dates)}")

    # Line item stats
    iv_lines = sum(1 for li in line_items if li['iv_doc_ref'].startswith('IV'))
    or_lines = sum(1 for li in line_items if li['iv_doc_ref'].startswith('OR'))
    print(f"\n  Line items: {len(line_items):,}")
    print(f"    From IV docs: {iv_lines:,}")
    print(f"    From OR docs: {or_lines:,}")

    # IV↔OR linking
    or_refs = set(li['or_doc_ref'] for li in line_items if li['or_doc_ref'])
    print(f"    Unique OR refs linked: {len(or_refs):,}")

    # Customer distribution
    cust_codes = defaultdict(int)
    for h in headers.values():
        cc = h.get('customer_code', '')
        if cc:
            cust_codes[cc] += 1
    print(f"\n  Unique customers: {len(cust_codes):,}")
    top_customers = sorted(cust_codes.items(), key=lambda x: -x[1])[:10]
    for cc, cnt in top_customers:
        cust_name = headers.get(next(
            (k for k, v in headers.items() if v['customer_code'] == cc), ''), {}).get('customer_name', '')
        print(f"    {cc}: {cnt:,} invoices  ({cust_name[:30]})")

    # Revenue summary
    total_revenue = sum(h['grand_total'] for h in headers.values())
    total_vat = sum(h['vat_amount'] for h in headers.values())
    print(f"\n  Total grand total: {total_revenue:,.2f}")
    print(f"  Total VAT: {total_vat:,.2f}")

    # ── 3. Join line items with headers ─────────────────────────────────────
    print("\n" + "=" * 80)
    print("JOINING HEADERS + LINE ITEMS")
    print("=" * 80)

    matched_lines = 0
    unmatched_lines = 0
    for li in line_items:
        iv_ref = li['iv_doc_ref']
        if iv_ref in headers:
            li['invoice_date'] = headers[iv_ref].get('invoice_date', '')
            li['customer_code'] = headers[iv_ref].get('customer_code', '')
            matched_lines += 1
        else:
            li['invoice_date'] = ''
            li['customer_code'] = ''
            unmatched_lines += 1

    print(f"  Matched to header: {matched_lines:,}")
    print(f"  No matching header: {unmatched_lines:,}")

    # ── 4. Write invoice headers CSV ────────────────────────────────────────
    print("\n" + "=" * 80)
    print("WRITING OUTPUTS")
    print("=" * 80)

    header_columns = [
        'invoice_number', 'doc_type', 'invoice_date', 'due_date',
        'customer_code', 'customer_name',
        'salesperson_code', 'payment_type', 'invoice_type',
        'credit_days', 'credit_term_code',
        'subtotal', 'net_amount', 'vat_rate', 'vat_amount', 'grand_total',
        'discount',
        'delivery_address',
        'void_date',
        'created_date', 'created_time',
        'tax_id',
    ]

    sorted_headers = sorted(headers.values(), key=lambda h: (h['invoice_date'] or '9999', h['invoice_number']))

    header_csv = os.path.join(OUTPUT_DIR, "invoice_headers.csv")
    with open(header_csv, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=header_columns, extrasaction='ignore')
        writer.writeheader()
        for rec in sorted_headers:
            writer.writerow(rec)
    print(f"  invoice_headers.csv: {len(sorted_headers):,} rows")

    # ── 5. Write line items CSV ─────────────────────────────────────────────
    line_item_columns = [
        'iv_doc_ref', 'or_doc_ref', 'invoice_date', 'customer_code',
        'line_number',
        'sku', 'sku_type', 'product_name', 'location',
        'qty', 'unit_cost', 'unit_price', 'total_cost', 'total_price',
        'salesperson_name',
    ]

    sorted_lines = sorted(line_items, key=lambda li: (li.get('invoice_date', '') or '9999', li['iv_doc_ref'], li.get('line_number', 0)))

    line_csv = os.path.join(OUTPUT_DIR, "invoice_line_items.csv")
    with open(line_csv, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=line_item_columns, extrasaction='ignore')
        writer.writeheader()
        for rec in sorted_lines:
            writer.writerow(rec)
    print(f"  invoice_line_items.csv: {len(sorted_lines):,} rows")

    # ── 6. Excel output (optional) ──────────────────────────────────────────
    try:
        import pandas as pd
        # Headers Excel
        df_h = pd.DataFrame(sorted_headers, columns=header_columns)
        xlsx_h = os.path.join(OUTPUT_DIR, "invoice_headers.xlsx")
        df_h.to_excel(xlsx_h, index=False, engine='openpyxl')
        print(f"  invoice_headers.xlsx: {len(sorted_headers):,} rows")

        # Line items Excel
        df_l = pd.DataFrame(sorted_lines, columns=line_item_columns)
        xlsx_l = os.path.join(OUTPUT_DIR, "invoice_line_items.xlsx")
        df_l.to_excel(xlsx_l, index=False, engine='openpyxl')
        print(f"  invoice_line_items.xlsx: {len(sorted_lines):,} rows")
    except ImportError:
        print("  pandas/openpyxl not available, skipping Excel output")
    except Exception as e:
        print(f"  Excel export error: {e}")
        print("  (CSV files were exported successfully)")

    # ── 7. Defensive validation ─────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("DEFENSIVE CHECKS")
    print("=" * 80)

    warnings_list = []

    # Header field count check
    if header_field_counts:
        max_hf = max(header_field_counts)
        min_hf = min(header_field_counts)
        if max_hf > EXPECTED_HEADER_FIELDS:
            msg = f"Header records have up to {max_hf} fields (expected {EXPECTED_HEADER_FIELDS})"
            print(f"\n  ⚠ {msg}")
            warnings_list.append(msg)
        else:
            print(f"\n  ✓ Header field count OK: {min_hf}–{max_hf} (expected {EXPECTED_HEADER_FIELDS})")

    # Line item field count check
    if line_item_field_counts:
        max_lf = max(line_item_field_counts)
        min_lf = min(line_item_field_counts)
        if max_lf > EXPECTED_LINE_ITEM_FIELDS:
            msg = f"Line item records have up to {max_lf} fields (expected {EXPECTED_LINE_ITEM_FIELDS})"
            print(f"  ⚠ {msg}")
            warnings_list.append(msg)
        else:
            print(f"  ✓ Line item field count OK: {min_lf}–{max_lf} (expected {EXPECTED_LINE_ITEM_FIELDS})")

    # Doc type check
    known_doc_types = {'IV', 'OR', ''}
    seen_doc_types = set(h['doc_type'] for h in headers.values())
    unknown_doc_types = seen_doc_types - known_doc_types
    if unknown_doc_types:
        msg = f"Unknown doc types in headers: {unknown_doc_types}"
        print(f"  ⚠ {msg}")
        warnings_list.append(msg)
    else:
        print(f"  ✓ All doc types are known: {seen_doc_types - {''}}")

    # VAT sanity check (sample 100 IV invoices)
    vat_errors = 0
    vat_checked = 0
    for h in list(headers.values())[:1000]:
        if h['doc_type'] == 'IV' and h['subtotal'] > 0 and h['vat_rate'] > 0:
            expected_vat = h['subtotal'] * h['vat_rate'] / 100
            actual_vat = h['vat_amount']
            if abs(expected_vat - actual_vat) > 1.0:  # Allow 1 baht rounding
                vat_errors += 1
            vat_checked += 1
    if vat_checked > 0:
        if vat_errors > 0:
            msg = f"VAT calculation mismatch in {vat_errors}/{vat_checked} sampled invoices"
            print(f"  ⚠ {msg}")
            warnings_list.append(msg)
        else:
            print(f"  ✓ VAT calculation verified on {vat_checked} invoices (subtotal × rate% ≈ vat_amount)")

    # Cross-check: do line items reference known IV headers?
    iv_doc_refs_in_lines = set(li['iv_doc_ref'] for li in line_items)
    iv_headers_set = set(k for k in headers.keys() if k.startswith('IV'))
    orphan_line_refs = iv_doc_refs_in_lines - set(headers.keys())
    if orphan_line_refs:
        print(f"  ⚠ {len(orphan_line_refs):,} line item doc_refs have no matching header")
    else:
        print(f"  ✓ All line item doc_refs match a header")

    # ── 8. Stats JSON ───────────────────────────────────────────────────────
    stats = {
        'version': 'v1',
        'timestamp': datetime.now().isoformat(),
        'source': 'DATA.CW/CVIVDMAS + CVIVDTRN',
        'total_headers': len(headers),
        'iv_headers': iv_headers,
        'or_headers': or_headers,
        'total_line_items': len(line_items),
        'iv_line_items': iv_lines,
        'or_line_items': or_lines,
        'unique_customers': len(cust_codes),
        'unique_or_refs': len(or_refs),
        'matched_lines': matched_lines,
        'unmatched_lines': unmatched_lines,
        'total_revenue': round(total_revenue, 2),
        'total_vat': round(total_vat, 2),
        'date_range': {
            'earliest': min(dates) if dates else '',
            'latest': max(dates) if dates else '',
        },
        'header_field_count': {
            'min': min(header_field_counts) if header_field_counts else 0,
            'max': max(header_field_counts) if header_field_counts else 0,
            'expected': EXPECTED_HEADER_FIELDS,
        },
        'line_item_field_count': {
            'min': min(line_item_field_counts) if line_item_field_counts else 0,
            'max': max(line_item_field_counts) if line_item_field_counts else 0,
            'expected': EXPECTED_LINE_ITEM_FIELDS,
        },
        'doc_type_breakdown': dict(sorted(
            defaultdict(int, {h['doc_type']: 0 for h in headers.values()}).items()
        )),
        'top_customers': [{'code': cc, 'count': cnt} for cc, cnt in top_customers[:20]],
    }

    # Count doc types properly
    doc_type_counts = defaultdict(int)
    for h in headers.values():
        doc_type_counts[h['doc_type']] += 1
    stats['doc_type_breakdown'] = dict(sorted(doc_type_counts.items(), key=lambda x: -x[1]))

    if warnings_list:
        stats['has_warnings'] = True
        stats['warnings'] = warnings_list

    stats_path = os.path.join(OUTPUT_DIR, "invoice_stats.json")
    with open(stats_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f"\n  invoice_stats.json: saved")

    # ── 9. Spot checks ──────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("SPOT CHECKS")
    print("=" * 80)

    # Show a few sample headers
    sample_ivs = [k for k in sorted(headers.keys()) if k.startswith('IV')][-5:]
    for iv in sample_ivs:
        h = headers[iv]
        lines_for_iv = [li for li in line_items if li['iv_doc_ref'] == iv]
        print(f"\n  {iv}: date={h['invoice_date']}  customer={h['customer_code']}")
        print(f"    subtotal={h['subtotal']}  VAT={h['vat_amount']}  total={h['grand_total']}")
        print(f"    name: {h['customer_name'][:40]}")
        print(f"    line items: {len(lines_for_iv)}")
        for li in lines_for_iv[:3]:
            print(f"      SKU={li['sku']:{20}s}  qty={li['qty']}  price={li['unit_price']}  OR={li['or_doc_ref']}")

    # Show a few sample OR headers
    sample_ors = [k for k in sorted(headers.keys()) if k.startswith('OR')][:3]
    for or_ref in sample_ors:
        h = headers[or_ref]
        print(f"\n  {or_ref}: date={h['invoice_date']}  customer={h['customer_code']}")
        print(f"    subtotal={h['subtotal']}  total={h['grand_total']}")

    t_end = time.time()
    print(f"\n{'=' * 80}")
    print(f"DONE! Total: {t_end - t_start:.1f}s (parse: {t_parse - t_start:.1f}s)")
    print(f"{'=' * 80}")
