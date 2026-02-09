#!/usr/bin/env python3
"""Split images folder into chunks of 5000 for parallel uploads.

Structure:
    .local/basedata/
    ├── images/      # Source (remaining < 5000 stay here)
    ├── ix1/         # First 5000
    ├── ix2/         # Next 5000
    └── ix3/         # Next 5000, etc.

Usage:
    # Dry run - show what would happen (default)
    python scripts/image_proxy/split_images.py
    
    # Actually move files
    python scripts/image_proxy/split_images.py --execute
    
    # Custom batch size
    python scripts/image_proxy/split_images.py --batch-size 3000 --execute
"""

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from common import PROJECT_ROOT


BASE_DIR = PROJECT_ROOT / ".local" / "basedata"
IMAGES_DIR = BASE_DIR / "images"
DEFAULT_BATCH_SIZE = 5000


def get_existing_ix_folders() -> list[int]:
    """Get existing ix folder numbers."""
    numbers = []
    for folder in BASE_DIR.iterdir():
        if folder.is_dir() and folder.name.startswith("ix"):
            try:
                num = int(folder.name[2:])
                numbers.append(num)
            except ValueError:
                pass
    return sorted(numbers)


def get_next_ix_number() -> int:
    """Calculate next ix folder number."""
    existing = get_existing_ix_folders()
    if existing:
        return max(existing) + 1
    return 1


def get_image_files(directory: Path) -> list[Path]:
    """Get all image files in directory."""
    extensions = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff", ".tif", ".avif"}
    files = []
    for f in sorted(directory.iterdir()):
        if f.is_file() and f.suffix.lower() in extensions:
            files.append(f)
    return files


def main():
    parser = argparse.ArgumentParser(description="Split images into folders of 5000")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, 
                        help=f"Images per folder (default: {DEFAULT_BATCH_SIZE})")
    parser.add_argument("--execute", action="store_true", 
                        help="Actually move files (default is dry-run)")
    
    args = parser.parse_args()
    
    if not IMAGES_DIR.exists():
        print(f"Error: Images directory not found: {IMAGES_DIR}")
        return
    
    # Get all images in source folder
    images = get_image_files(IMAGES_DIR)
    total = len(images)
    
    print(f"Images in {IMAGES_DIR.name}/: {total}")
    print(f"Batch size: {args.batch_size}")
    
    # Check existing ix folders
    existing_ix = get_existing_ix_folders()
    if existing_ix:
        print(f"Existing ix folders: {['ix' + str(n) for n in existing_ix]}")
    
    # Calculate how many complete batches we can make
    # Leave remainder (< batch_size) in images/
    complete_batches = total // args.batch_size
    remainder = total % args.batch_size
    
    if complete_batches == 0:
        print(f"\nOnly {total} images (< {args.batch_size}). Nothing to split.")
        return
    
    print(f"\nWill create {complete_batches} batch(es), {remainder} images remain in images/")
    
    # Determine starting ix number
    next_ix = get_next_ix_number()
    
    # Move images in batches
    moved_total = 0
    for batch_num in range(complete_batches):
        ix_name = f"ix{next_ix + batch_num}"
        ix_dir = BASE_DIR / ix_name
        
        start_idx = batch_num * args.batch_size
        end_idx = start_idx + args.batch_size
        batch_images = images[start_idx:end_idx]
        
        print(f"\n{ix_name}/: {len(batch_images)} images (index {start_idx}-{end_idx-1})")
        
        if not args.execute:
            print(f"  [DRY RUN] Would create {ix_dir}")
            print(f"  [DRY RUN] Would move: {batch_images[0].name} ... {batch_images[-1].name}")
        else:
            ix_dir.mkdir(exist_ok=True)
            for img in batch_images:
                dest = ix_dir / img.name
                shutil.move(str(img), str(dest))
                moved_total += 1
            print(f"  Moved {len(batch_images)} images")
    
    # Summary
    print("\n" + "=" * 50)
    if not args.execute:
        print("[DRY RUN] No files were moved. Use --execute to actually move files.")
    else:
        print(f"Moved {moved_total} images to {complete_batches} folder(s)")
    
    remaining = get_image_files(IMAGES_DIR)
    print(f"Remaining in images/: {len(remaining)}")
    
    all_ix = get_existing_ix_folders()
    if all_ix:
        print(f"All ix folders: {['ix' + str(n) for n in all_ix]}")


if __name__ == "__main__":
    main()
