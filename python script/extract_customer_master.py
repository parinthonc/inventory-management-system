"""
Extract Customer Master from server binary files.
Source: DATA.CW/CVARDMAS (main customer data, ~8.4 MB, 123 fields per record).
Thai text is decoded via a custom byte mapping (the ERP uses a non-standard Thai encoding).
Field mapping verified by cross-referencing ZARD4120 sample report against binary records.
Outputs: customer_master.csv, customer_master.xlsx
"""
import csv, os, sys, json, re
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = r"Z:\DATA.CW"
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_SCRIPT_DIR)  # parent of "python script"
OUT_DIR = os.path.join(_PROJECT_DIR, "customer master table")
DELIM = 0x8A

# ── Custom ERP Thai encoding → TIS-620 byte mapping ────────────────────────
# The ERP system stores Thai text using a non-standard character ordering.
# This table maps each custom byte to the correct TIS-620 byte.
# Built by cross-referencing ~15,700 product records with 100% accuracy.
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

EXPECTED_FIELD_COUNT = 123  # Known number of fields per customer record

# ── Field mapping (0x8A-delimited, 123 fields per record) ──────────────────
# Verified by cross-referencing ZARD4120 sample report with binary data.
# Fields matched: C01003, C01088, C01093, C01095, C01099, C01104
FIELD_MAP = {
    0:  'customer_code',
    1:  'customer_name_th_raw',        # Thai (custom encoding)
    2:  'customer_name_2',             # Usually empty, secondary name
    3:  'address_raw',                 # Thai address
    4:  'phone',
    5:  'fax',
    6:  'field_06',                    # Usually empty
    7:  'contact_person_raw',          # Thai contact name
    8:  'field_08',                    # Usually empty
    9:  'field_09',                    # Usually empty
    10: 'salesperson_code',            # e.g. "005", "023", "300"
    11: 'field_11',                    # Usually empty
    12: 'date_opened',                 # Account open date (DD/MM/YY BE)
    13: 'field_13',
    14: 'field_14',
    15: 'field_15',
    16: 'date_last_invoice',           # Last invoice date
    17: 'last_invoice_no',             # e.g. "IV650045"
    18: 'date_last_payment',           # Last payment received date
    19: 'last_receipt_no',             # e.g. "091/049"
    20: 'date_20',                     # Additional date field
    21: 'field_21',
    22: 'status_code',                 # "00" = active, "01" = inactive
    23: 'field_23',
    24: 'tax_id',                      # 13-digit Thai tax ID
    25: 'branch_type',                 # "E" = สำนักงานใหญ่ (HQ), "D" = สาขา (branch)
    26: 'branch_number',               # "1" for HQ
    27: 'credit_limit',               # e.g. "00000"
    28: 'collection_schedule_raw',     # Thai text, e.g. "ทุกวัน", "ทุกวันพฤหัสบดี"
    29: 'collection_note_raw',         # Thai text, e.g. "ครบกำหนดแล้วไปเก็บ"
    30: 'credit_days',                 # e.g. "30", "60"
}

# Monthly data fields (12 months each, similar to product master)
# Fields 31-122 contain periodic transaction totals
MONTHLY_SALES_QTY = list(range(34, 46))     # Fields 34-45 (12 months)
MONTHLY_SALES_VAL = list(range(46, 58))     # Fields 46-57 (12 months)
MONTHLY_RECEIPT_QTY = list(range(58, 70))   # Fields 58-69 (12 months)
MONTHLY_RECEIPT_VAL = list(range(70, 82))   # Fields 70-81 (12 months)


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
    if not date_str or '/' not in date_str or date_str.strip() in ('', '/  /', '/ /', '  /  /'):
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
    if not val or not val.strip():
        return 0.0
    try:
        return float(val.strip().replace(',', ''))
    except (ValueError, OverflowError):
        return 0.0


def parse_cvardmas():
    """Parse CVARDMAS binary → list of customer records with decoded Thai text."""
    filepath = os.path.join(BASE, "CVARDMAS")
    with open(filepath, 'rb') as f:
        data = f.read()

    fsize = len(data)
    records = []
    field_count_stats = []  # Track field counts for validation
    pos = 0x200  # Skip 512-byte B-tree header

    while pos < fsize - 50:
        b = data[pos]
        if b == 0 or b == 0x20:
            pos += 1
            continue

        chunk = data[pos:pos+30]
        delim_pos = chunk.find(bytes([DELIM]))

        if 3 <= delim_pos <= 15:
            potential_code = chunk[:delim_pos].decode('ascii', errors='replace').strip()
            # Valid customer codes are alphanumeric (e.g. C01003, A29046, APC182, 27453).
            # Reject phone numbers (0-2147-4918), dates (01/01/47), and other stray data
            # by requiring: no hyphens, slashes, spaces, commas, dots, or parens.
            if (len(potential_code) >= 4
                    and all(c >= ' ' and c < '\x7f' for c in potential_code)
                    and re.match(r'^[A-Za-z0-9]+$', potential_code)):
                # Find record end (4 consecutive null bytes)
                # Some records are >1000 bytes (e.g. C20002 = 1125 bytes),
                # so search up to 2000 bytes ahead.
                rec_end = pos + delim_pos
                for i in range(pos + delim_pos, min(pos + 2000, fsize - 4)):
                    if data[i:i+4] == b'\x00\x00\x00\x00':
                        rec_end = i
                        break

                fields_raw = data[pos:rec_end].split(bytes([DELIM]))

                # Proper customer records have ~123 fields; reject short fragments
                if len(fields_raw) >= 80:
                    field_count_stats.append(len(fields_raw))
                    rec = {}

                    # Extract ASCII fields
                    for fi, fname in FIELD_MAP.items():
                        if fi < len(fields_raw):
                            val = fields_raw[fi].decode('ascii', errors='replace').strip()
                            rec[fname] = val
                        else:
                            rec[fname] = ''

                    # Decode Thai text fields using custom mapping
                    if len(fields_raw) > 1:
                        rec['customer_name'] = decode_thai(fields_raw[1])
                    else:
                        rec['customer_name'] = ''

                    if len(fields_raw) > 3:
                        rec['address'] = decode_thai(fields_raw[3])
                    else:
                        rec['address'] = ''

                    if len(fields_raw) > 7:
                        rec['contact_person'] = decode_thai(fields_raw[7])
                    else:
                        rec['contact_person'] = ''

                    if len(fields_raw) > 28:
                        rec['collection_schedule'] = decode_thai(fields_raw[28])
                    else:
                        rec['collection_schedule'] = ''

                    if len(fields_raw) > 29:
                        rec['collection_note'] = decode_thai(fields_raw[29])
                    else:
                        rec['collection_note'] = ''

                    # Convert dates
                    for date_field in ['date_opened', 'date_last_invoice',
                                       'date_last_payment', 'date_20']:
                        rec[date_field] = convert_be_date(rec.get(date_field, ''))

                    # Numeric fields
                    rec['credit_days'] = safe_float(rec.get('credit_days', ''))
                    rec['credit_limit'] = safe_float(rec.get('credit_limit', ''))

                    # Map branch type to Thai name
                    branch_type = rec.get('branch_type', '')
                    if branch_type == 'E':
                        rec['branch_type_name'] = 'สำนักงานใหญ่'
                    elif branch_type == 'D':
                        rec['branch_type_name'] = 'สาขา'
                    else:
                        rec['branch_type_name'] = branch_type

                    # Map status code
                    status = rec.get('status_code', '')
                    if status == '00':
                        rec['status'] = 'active'
                    elif status == '01':
                        rec['status'] = 'inactive'
                    else:
                        rec['status'] = status

                    # Monthly totals (sum 12 months)
                    total_sales = sum(safe_float(fields_raw[fi].decode('ascii', errors='replace').strip())
                                      for fi in MONTHLY_SALES_VAL if fi < len(fields_raw))
                    total_receipts = sum(safe_float(fields_raw[fi].decode('ascii', errors='replace').strip())
                                         for fi in MONTHLY_RECEIPT_VAL if fi < len(fields_raw))
                    rec['annual_sales_value'] = total_sales
                    rec['annual_receipts_value'] = total_receipts

                    # Clean up raw fields
                    for raw_field in ['customer_name_th_raw', 'address_raw',
                                      'contact_person_raw', 'collection_schedule_raw',
                                      'collection_note_raw']:
                        rec.pop(raw_field, None)

                    # Remove internal fields
                    for internal in ['field_06', 'field_08', 'field_09', 'field_11',
                                     'field_13', 'field_14', 'field_15', 'field_21',
                                     'field_23', 'customer_name_2']:
                        rec.pop(internal, None)

                    records.append(rec)
                    pos = rec_end
                    continue
        pos += 1

    # Post-parse validation: only keep records with valid customer codes.
    # Valid codes start with 'C' followed by digits (e.g. C01003, C29046),
    # plus the single known exception 'APC182'.
    valid_records = []
    rejected_codes = []
    for rec in records:
        code = rec.get('customer_code', '')
        if re.match(r'^C\d', code) or code == 'APC182':
            valid_records.append(rec)
        else:
            rejected_codes.append(code)

    if rejected_codes:
        print(f"  ⚠ Rejected {len(rejected_codes)} records with invalid customer codes:")
        # Show sample of rejected codes
        for code in rejected_codes[:20]:
            print(f"      '{code}'")
        if len(rejected_codes) > 20:
            print(f"      ... and {len(rejected_codes) - 20} more")

    return valid_records, field_count_stats


def main():
    print("=" * 80)
    print("CUSTOMER MASTER EXTRACTION")
    print("Source: DATA.CW/CVARDMAS")
    print("=" * 80)

    # ── 1. Parse customer data ──────────────────────────────────────────────
    print(f"\nParsing CVARDMAS...")
    records, field_count_stats = parse_cvardmas()
    print(f"  Extracted {len(records):,} customer records")

    # ── 2. Summary statistics ───────────────────────────────────────────────
    active_count = sum(1 for r in records if r['status'] == 'active')
    inactive_count = sum(1 for r in records if r['status'] == 'inactive')
    with_tax_id = sum(1 for r in records if r.get('tax_id', ''))
    with_phone = sum(1 for r in records if r.get('phone', ''))
    with_address = sum(1 for r in records if r.get('address', ''))

    print(f"  Active: {active_count:,}")
    print(f"  Inactive: {inactive_count:,}")
    print(f"  Other status: {len(records) - active_count - inactive_count:,}")
    print(f"  With tax ID: {with_tax_id:,}")
    print(f"  With phone: {with_phone:,}")
    print(f"  With address: {with_address:,}")

    # Salesperson distribution
    sp_codes = {}
    for r in records:
        sp = r.get('salesperson_code', '')
        if sp:
            sp_codes[sp] = sp_codes.get(sp, 0) + 1
    print(f"\n  Salesperson codes: {len(sp_codes)} unique")
    top_sp = sorted(sp_codes.items(), key=lambda x: -x[1])[:10]
    for code, count in top_sp:
        print(f"    {code}: {count} customers")

    # ── 3. Write CSV output ─────────────────────────────────────────────────
    csv_columns = [
        'customer_code', 'customer_name', 'status', 'tax_id',
        'address', 'phone', 'fax',
        'contact_person', 'salesperson_code',
        'branch_type', 'branch_number', 'branch_type_name',
        'credit_limit', 'credit_days',
        'collection_schedule', 'collection_note',
        'date_opened', 'date_last_invoice', 'last_invoice_no',
        'date_last_payment', 'last_receipt_no', 'date_20',
        'status_code',
        'annual_sales_value', 'annual_receipts_value',
    ]

    sorted_records = sorted(records, key=lambda r: r['customer_code'])

    out_csv = os.path.join(OUT_DIR, "customer_master.csv")
    with open(out_csv, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=csv_columns, extrasaction='ignore')
        writer.writeheader()
        for rec in sorted_records:
            writer.writerow(rec)
    print(f"\n  CSV: {out_csv}")
    print(f"  {len(sorted_records):,} rows")

    # ── 4. Excel output ─────────────────────────────────────────────────────
    try:
        import pandas as pd
        df = pd.DataFrame(sorted_records, columns=csv_columns)
        out_xlsx = os.path.join(OUT_DIR, "customer_master.xlsx")
        df.to_excel(out_xlsx, index=False, engine='openpyxl')
        print(f"  Excel: {out_xlsx}")
        print(f"  {len(sorted_records):,} rows")
    except ImportError:
        print("\n  pandas/openpyxl not available, skipping Excel output")
    except Exception as e:
        print(f"\n  Excel export error: {e}")
        print("  (CSV was exported successfully)")

    # ── 5. Stats JSON ───────────────────────────────────────────────────────
    stats = {
        'total_records': len(records),
        'active': active_count,
        'inactive': inactive_count,
        'with_tax_id': with_tax_id,
        'with_phone': with_phone,
        'with_address': with_address,
        'salesperson_distribution': dict(sorted(sp_codes.items(), key=lambda x: -x[1])),
        'extracted_at': datetime.now().isoformat(),
    }
    # ── DEFENSIVE VALIDATION WARNINGS ────────────────────────────────────────
    # Detect if ERP has been updated with new fields we're not capturing.
    print(f"\n{'=' * 60}")
    print("DEFENSIVE CHECKS")
    print(f"{'=' * 60}")

    if field_count_stats:
        max_fields = max(field_count_stats)
        min_fields = min(field_count_stats)
        avg_fields = sum(field_count_stats) / len(field_count_stats)
        over_expected = sum(1 for c in field_count_stats if c > EXPECTED_FIELD_COUNT)

        if max_fields > EXPECTED_FIELD_COUNT:
            print(f"\n  ⚠ NEW FIELDS DETECTED: some records have {max_fields} fields")
            print(f"    (expected {EXPECTED_FIELD_COUNT}). {over_expected:,} records affected.")
            print(f"    → The ERP may have been updated. Fields {EXPECTED_FIELD_COUNT}–{max_fields-1} are NOT being captured.")
            print(f"    → Update FIELD_MAP to include new fields if needed.")
        else:
            print(f"\n  ✓ Field count OK: all records have ≤{EXPECTED_FIELD_COUNT} fields (max={max_fields})")

        if min_fields < EXPECTED_FIELD_COUNT:
            under = sum(1 for c in field_count_stats if c < EXPECTED_FIELD_COUNT)
            print(f"  ⚠ {under:,} records have fewer than {EXPECTED_FIELD_COUNT} fields (min={min_fields})")
            print(f"    → Some records may have missing data.")

        print(f"  ✓ Field count range: {min_fields}–{max_fields} (avg {avg_fields:.0f})")

        # Check for unknown status codes
        known_statuses = {'00', '01'}
        seen_statuses = set(r.get('status_code', '') for r in records if r.get('status_code', ''))
        unknown_statuses = seen_statuses - known_statuses
        if unknown_statuses:
            print(f"\n  ⚠ UNKNOWN STATUS CODES: {unknown_statuses}")
            for s in sorted(unknown_statuses):
                count = sum(1 for r in records if r.get('status_code', '') == s)
                print(f"      '{s}': {count} records")
        else:
            print(f"  ✓ All status codes are known ({seen_statuses})")

        # Check for unknown branch types
        known_branches = {'E', 'D', ''}
        seen_branches = set(r.get('branch_type', '') for r in records)
        unknown_branches = seen_branches - known_branches
        if unknown_branches:
            print(f"  ⚠ UNKNOWN BRANCH TYPES: {unknown_branches}")
        else:
            print(f"  ✓ All branch types are known")
    else:
        print("\n  ⚠ No records parsed — cannot validate.")

    stats['field_count_range'] = {
        'min': min(field_count_stats) if field_count_stats else 0,
        'max': max(field_count_stats) if field_count_stats else 0,
        'expected': EXPECTED_FIELD_COUNT,
    }
    if field_count_stats and max(field_count_stats) > EXPECTED_FIELD_COUNT:
        stats['has_warnings'] = True
        stats['warnings'] = [f"Records have up to {max(field_count_stats)} fields, expected {EXPECTED_FIELD_COUNT}"]

    stats_path = os.path.join(OUT_DIR, "customer_master_stats.json")
    with open(stats_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f"  Stats: {stats_path}")

    print("\nDone!")


if __name__ == '__main__':
    main()
