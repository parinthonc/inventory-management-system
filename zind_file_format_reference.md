# ZIND File Format — Complete Reference

## What is a ZIND File?

A **ZIND file** is a **daily inventory snapshot** exported from a **legacy Thai ERP system**. It is a **pipe-delimited (`|`) plain text file** that contains a complete listing of all products in inventory, including part numbers, names (Thai + English), quantities, prices, and costs.

> [!IMPORTANT]
> ZIND files represent the **previous day's** inventory. They are generated in the morning and contain data as of the end of the prior business day.

---

## File Naming Convention

```
ZIND4140_BBBB-MM-DD_HH-MM-SS.TXT
```

| Part | Meaning |
|------|---------|
| `ZIND4140` | Report code / identifier from the ERP system |
| `BBBB` | Year in **Buddhist Era** (Thai calendar). Subtract 543 to get Gregorian year. (e.g., `2569` = 2026 CE) |
| `MM-DD` | Month and Day |
| `HH-MM-SS` | Time the file was generated |

**Example:** `ZIND4140_2569-02-25_07-47-55.TXT` → Generated on Feb 25, 2569 BE (= Feb 25, 2026 CE) at 07:47:55, representing inventory as of **Feb 24, 2026**.

---

## File Encoding

- **Encoding:** Windows-874 / CP874 (Thai character encoding)
- **Common issue:** Some files may have **Mojibake** (double-encoded text). The fix is:
  ```
  Decode as Latin-1 → Re-encode as Latin-1 → Decode as CP874
  ```
- **Fallback:** Decode directly as CP874 with `errors='ignore'`
- **File size:** ~3.4–3.6 MB per file (typically ~15,000+ data lines)

---

## File Structure

The file has **4 line types**, identified by the **first character before the first pipe**:

### 1. Format Line (`F|`) — 1 line, always first

Defines the **column data types** for the data rows.

```
F|A|A|A|A|A|A|A|I|N|N|N
```

| Type Code | Meaning |
|-----------|---------|
| `A` | Alphanumeric (text) |
| `I` | Integer |
| `N` | Numeric (decimal) |

This tells you columns 0–7 are text, column 8 is integer, columns 9–11 are numeric.

> [!NOTE]
> Some older ZIND files may only have `F|A|A|A|A|A|A|A|I` (9 fields) — these are **missing the Price and Cost columns** (fields 9 and 10) and need to be backfilled.

### 2. Header Line (`H|`) — 1 line

The **report title** in Thai.

```
H|รายงานรายการสินค้า
```

Translation: "Product Inventory Report"

### 3. Title/Column Header Line (`T|`) — 1 line

Defines **column names** (in Thai and English) for the data rows.

```
T|รหัสสินค้า|ประเภท|คลังสินค้า|Name|รายการสินค้า|ขนาดสินค้า|ยี่ห้อ|จำนวนสินค้า|ราคาขาย|Unit cost|ราคาตลาด
```

### 4. Data Lines (`D|`) — Thousands of lines (the actual inventory)

Each line represents **one SKU in one warehouse location**.

```
D|Code.001-20635001        |G|Q33|                              |แหวนล็อค                          |Code.                |KATO      |      1|       80.00|        1.00|        0.00
```

---

## Data Line Column Map (Pipe-Delimited)

After splitting by `|` and stripping whitespace:

| Index | Thai Column Name | English Name | Description | Example |
|-------|-----------------|--------------|-------------|---------|
| 0 | — | Row Type | Always `D` for data | `D` |
| 1 | รหัสสินค้า | Part Code | Prefixed with `Code.` → strip this prefix to get the actual part number | `Code.001-20635001` → `001-20635001` |
| 2 | ประเภท | Suffix / Type | Item classification suffix (G, N, L, R, C, etc.) | `G` |
| 3 | คลังสินค้า | Warehouse | Warehouse/location code | `Q33`, `R26`, `2B2`, `T31` |
| 4 | Name | English Name | Product name in English (may be empty) | `O'RING`, `BOLT`, `NUT LOCK` |
| 5 | รายการสินค้า | Thai Name | Product description in Thai | `โอริง`, `สกรู`, `แหวนล็อค` |
| 6 | ขนาดสินค้า | Size/Spec | Size or specification. Also prefixed with `Code.` | `Code.P-14` → `P-14` |
| 7 | ยี่ห้อ | Brand | Manufacturer/brand name | `KATO`, `KOMATSU`, `TCM`, `TOYOTA FORKLIFT` |
| 8 | จำนวนสินค้า | Quantity | Current stock quantity (integer, may have commas) | `1`, `50`, `2,000` |
| 9 | ราคาขาย | Sale Price | Selling price per unit (decimal, may have commas) | `80.00`, `11,200.00` |
| 10 | Unit cost | Unit Cost | Cost/purchase price per unit (decimal, may have commas) | `1.00`, `7,472.00` |
| 11 | ราคาตลาด | Market Price | Market reference price (decimal, often `0.00`) | `0.00`, `13,200.00` |

> [!WARNING]
> **Older files may only have 9 fields (indexes 0–8)**, missing Sale Price (9), Unit Cost (10), and Market Price (11). The `backfill_prices.py` script was created to retroactively add these columns.

---

## Suffix/Type Codes (Field Index 2)

The suffix classifies each item and is used to create a **composite SKU** in the format `{PartNumber}_{Suffix}`:

| Suffix | Meaning |
|--------|---------|
| `G` | **Genuine** (OEM) parts |
| `N` | **Japanese-made** non-genuine parts |
| `L` | **Locally-made** non-genuine parts |
| `R` | **Chinese-made** parts |
| `C` | **Chinese budget quality** parts |

**Example SKU construction:** Part code `01050-31030` + Suffix `G` → SKU = `01050-31030_G`

> [!IMPORTANT]
> The **same part number can appear multiple times** with different suffixes. For example, `01010-80816_G` (genuine) and `01010-80816_L` (local) are treated as **separate SKUs**.

---

## Continuation Rows

A product may be stored across **multiple warehouse locations**. In this case, additional rows appear for the same product where **Field 1 (Part Code) is empty** (just `Code.` with no number after it, yielding an empty string after stripping the prefix).

**Example:**
```
D|Code.04111-20302-71R     |R|T31|GASKET KIT 4Y 8FG  |ปะเก็นชุดยกเครื่อง 4Y 8FG|Code.ปะเก็นฝาสูบเหล็ก|TOYOTA FORKLIFT|      0|   1,600.00|      778.00|        0.00
D|                         | |T32|                    |                         |                     |               |     16|           |            |
```

The **second line** is a continuation row — it has no part code, and its quantity (`16`) should be **summed** with the main row's quantity (`0`) to get the total: **16 units**.

**How to detect:** After splitting by `|`, if `parts[1].replace("Code.", "").strip()` is **empty**, it is a continuation of the previous SKU.

---

## Whitespace / Padding

Fields are **right-padded with spaces** to fixed widths for visual alignment when viewed in a text editor. Always **strip whitespace** after splitting by `|`.

Numeric fields (Quantity, Price, Cost) are **right-aligned** within their fixed-width columns and may contain **commas** as thousands separators (e.g., `11,200.00`, `2,000`).

---

## Reading Algorithm (Python Pseudocode)

```python
# 1. Read file as binary
with open(filepath, 'rb') as f:
    raw_data = f.read()

# 2. Fix encoding (handle potential Mojibake)
try:
    text = raw_data.decode('latin-1').encode('latin-1').decode('cp874')
except:
    text = raw_data.decode('cp874', errors='ignore')

# 3. Parse lines
items = {}
last_sku = None

for line in text.splitlines():
    line = line.strip()
    if not line.startswith('D|'):
        continue  # Skip F|, H|, T| lines
    
    fields = [f.strip() for f in line.split('|')]
    if len(fields) < 8:
        continue
    
    part_code = fields[1].replace("Code.", "").strip()
    
    if not part_code:
        # Continuation row — add quantity to previous SKU
        if last_sku and last_sku in items:
            qty = parse_number(fields[8])  # strip commas, convert
            items[last_sku]['qty'] += qty
        continue
    
    suffix = fields[2].strip()
    sku = f"{part_code}_{suffix}"
    
    items[sku] = {
        'sku': sku,
        'name_eng': fields[4],      # English name
        'name_thai': fields[5],     # Thai name  
        'size': fields[6].replace("Code.", "").strip(),
        'brand': fields[7],
        'qty': parse_number(fields[8]),
        'sale_price': parse_number(fields[9]) if len(fields) >= 11 else 0,
        'unit_cost': parse_number(fields[10]) if len(fields) >= 11 else 0,
        'suffix': suffix
    }
    last_sku = sku
```

---

## Complete Example

### Raw File (first 4 lines):
```
F|A|A|A|A|A|A|A|I|N|N|N
H|รายงานรายการสินค้า
T|รหัสสินค้า|ประเภท|คลังสินค้า|Name|รายการสินค้า|ขนาดสินค้า|ยี่ห้อ|จำนวนสินค้า|ราคาขาย|Unit cost|ราคาตลาด
D|Code.009-65901001        |G|Q33|SWIVEL JOINT ASSY.              |ตัวต่อสายไฮโดลิก NK-160,200     |Code.052-60803001/2 ชุดซ่อม      |KATO      |      3|   11,200.00|    7,472.00|   13,200.00
```

### Parsed Result:
```json
{
  "sku": "009-65901001_G",
  "name_eng": "SWIVEL JOINT ASSY.",
  "name_thai": "ตัวต่อสายไฮโดลิก NK-160,200",
  "size": "052-60803001/2 ชุดซ่อม",
  "brand": "KATO",
  "qty": 3,
  "sale_price": 11200.00,
  "unit_cost": 7472.00,
  "suffix": "G"
}
```

---

## Key Gotchas

1. **Encoding:** Must handle CP874 (Thai Windows encoding), sometimes with Mojibake fix
2. **`Code.` prefix:** Fields 1 and 6 are prefixed with `Code.` — must be stripped
3. **Commas in numbers:** Quantities and prices may contain commas (`11,200.00`)
4. **Continuation rows:** Same product in multiple warehouses → empty Part Code field → sum quantities
5. **Same part, different suffix:** `01010-80816_G` and `01010-80816_L` are separate SKUs
6. **Missing price columns:** Older files may lack fields 9–11 (only 9 fields total instead of 12)
7. **Date logic:** The file's **modification date minus 1 day** = actual inventory date
8. **Buddhist Era dates:** Filenames use Thai Buddhist calendar (year + 543)
9. **Messy text in quantity field:** Some files have text like "10 pcs" in qty — split by space, take first token
10. **Trailing R in part codes:** Some SKUs have a trailing `R` (e.g., `04111-20302-71R`) — in some contexts this is stripped to find the "base" part number
