"""
Backfill script: Generate _thumb_ thumbnails for all existing product images.

Run this ONCE after deploying the thumbnail feature to create small (300px)
thumbnails for every existing image that doesn't already have one.

Usage:
    python generate_thumbnails.py

This only needs to be run once. After this, new uploads will automatically
generate thumbnails via the upload handler in server.py.
"""

import os
import sys
import configparser

# Load config using same logic as build_db.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

config = configparser.ConfigParser()
config.read([
    os.path.join(BASE_DIR, 'config.default.ini'),
    os.path.join(BASE_DIR, 'config.ini'),
    os.path.join(BASE_DIR, 'config.local.ini'),
])

IMAGE_DIR_CUSTOM = config.get('images', 'custom_dir', fallback='').strip()
if IMAGE_DIR_CUSTOM and not os.path.isabs(IMAGE_DIR_CUSTOM):
    IMAGE_DIR_CUSTOM = os.path.join(BASE_DIR, IMAGE_DIR_CUSTOM)

THUMB_MAX_DIMENSION = 300
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}


def generate_thumbnail(image_path, thumb_path):
    """Generate a small thumbnail from a full-size image."""
    try:
        from PIL import Image
        img = Image.open(image_path)
        if img.mode in ('RGBA', 'P', 'LA'):
            img = img.convert('RGB')
        w, h = img.size
        if max(w, h) > THUMB_MAX_DIMENSION:
            ratio = THUMB_MAX_DIMENSION / max(w, h)
            new_size = (int(w * ratio), int(h * ratio))
            img = img.resize(new_size, Image.LANCZOS)
        img.save(thumb_path, 'JPEG', quality=75, optimize=True)
        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        return False


def main():
    if not IMAGE_DIR_CUSTOM or not os.path.isdir(IMAGE_DIR_CUSTOM):
        print(f"Custom image directory not found: {IMAGE_DIR_CUSTOM}")
        sys.exit(1)

    print(f"Scanning: {IMAGE_DIR_CUSTOM}")
    print(f"Thumbnail size: {THUMB_MAX_DIMENSION}px max")
    print()

    total_images = 0
    generated = 0
    skipped = 0
    errors = 0

    # Walk through all SKU folders
    for sku_folder in sorted(os.listdir(IMAGE_DIR_CUSTOM)):
        folder_path = os.path.join(IMAGE_DIR_CUSTOM, sku_folder)
        if not os.path.isdir(folder_path):
            continue

        # Find all image files (not starting with _)
        files = [f for f in os.listdir(folder_path)
                 if os.path.isfile(os.path.join(folder_path, f))
                 and not f.startswith('_')
                 and os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS]

        if not files:
            continue

        for f in files:
            total_images += 1
            thumb_name = f'_thumb_{f}'
            thumb_path = os.path.join(folder_path, thumb_name)

            # Skip if thumbnail already exists
            if os.path.isfile(thumb_path):
                skipped += 1
                continue

            image_path = os.path.join(folder_path, f)
            orig_size = os.path.getsize(image_path)

            if generate_thumbnail(image_path, thumb_path):
                thumb_size = os.path.getsize(thumb_path)
                ratio = (1 - thumb_size / orig_size) * 100 if orig_size > 0 else 0
                print(f"  ✓ {sku_folder}/{f}: {orig_size//1024}KB → {thumb_size//1024}KB ({ratio:.0f}% smaller)")
                generated += 1
            else:
                errors += 1

    print()
    print(f"Done!")
    print(f"  Total images:     {total_images}")
    print(f"  Thumbnails made:  {generated}")
    print(f"  Already existed:  {skipped}")
    print(f"  Errors:           {errors}")

    if generated > 0:
        print()
        print("Next step: Rebuild the database to update thumbnail paths:")
        print("  python build_db.py")


if __name__ == '__main__':
    main()
