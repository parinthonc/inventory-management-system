import os
import sys

filepath = r'D:\CW\inventory management system\ZIND4140_2569-03-02_08-00-31.TXT'

with open(filepath, 'rb') as f:
    raw = f.read()

try:
    text = raw.decode('latin-1').encode('latin-1').decode('cp874')
except:
    text = raw.decode('cp874', errors='ignore')

lines = text.splitlines()
print(f"Total lines: {len(lines)}")

# Count line types
data_count = 0
brands = set()
sample_data = []
for line in lines:
    line = line.strip()
    if not line:
        continue
    if line.startswith('D|'):
        data_count += 1
        fields = [f.strip() for f in line.split('|')]
        if len(fields) >= 8:
            part_code = fields[1].replace("Code.", "").strip()
            if part_code and data_count <= 5:
                sample_data.append(fields)
            if part_code and fields[7].strip():
                brands.add(fields[7].strip())
    elif line.startswith('F|') or line.startswith('H|') or line.startswith('T|'):
        print(f"Header line: {line[:200]}")

print(f"\nData lines: {data_count}")
print(f"\nUnique brands ({len(brands)}): {sorted(brands)[:30]}")

print("\nSample data rows:")
for fields in sample_data[:5]:
    part_code = fields[1].replace("Code.", "").strip()
    suffix = fields[2]
    name_eng = fields[4]
    brand = fields[7]
    qty = fields[8] if len(fields) > 8 else ''
    price = fields[9] if len(fields) > 9 else ''
    print(f"  Part: {part_code} | Suffix: {suffix} | Eng: {name_eng} | Brand: {brand} | Qty: {qty} | Price: {price}")

# Check image directory
img_dir = r'C:\Users\Jan\Documents\CW\results_images\image'
test_part = '001-20635001'
part_dir = os.path.join(img_dir, test_part)
if os.path.exists(part_dir):
    imgs = sorted(os.listdir(part_dir))
    print(f"\nImages for {test_part}: {imgs}")

test_part2 = '009-65901001'
part_dir2 = os.path.join(img_dir, test_part2)
if os.path.exists(part_dir2):
    imgs2 = sorted(os.listdir(part_dir2))
    print(f"Images for {test_part2}: {imgs2}")
