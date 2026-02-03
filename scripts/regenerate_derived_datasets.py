#!/usr/bin/env python3
"""
Regenerate all derived TSV files from JSONL source.

This script reads the clean JSONL file and regenerates:
- datasource.tsv (main dataset)
- dataset_proper.tsv (unique products by thumbnail_urls)
- dataset_duplicated.tsv (duplicated products)
- datasource_complete.tsv (has AI estimates)
- datasource_incomplete.tsv (missing AI estimates)
- missing_estimations.tsv (has actual but no AI estimates)

Usage:
    python scripts/regenerate_derived_datasets.py
"""

import json
import csv
import shutil
from pathlib import Path
from collections import defaultdict
from datetime import datetime


def get_project_root() -> Path:
    """Get project root directory."""
    return Path(__file__).parent.parent


def read_jsonl(jsonl_path: Path) -> list[dict]:
    """Read all records from JSONL file."""
    records = []
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def sanitize_field(value) -> str:
    """Sanitize a field value for TSV output."""
    if value is None:
        return ''
    text = str(value)
    text = text.replace('\n', ' ')
    text = text.replace('\r', ' ')
    text = text.replace('\t', ' ')
    while '  ' in text:
        text = text.replace('  ', ' ')
    return text.strip()


def backup_file(file_path: Path, backup_dir: Path) -> Path | None:
    """Backup a file if it exists. Returns backup path or None."""
    if not file_path.exists():
        return None
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = backup_dir / f"{file_path.stem}_backup_{timestamp}{file_path.suffix}"
    shutil.copy2(file_path, backup_path)
    return backup_path


def write_tsv(records: list[dict], columns: list[str], output_path: Path, backup_dir: Path | None = None) -> tuple[int, Path | None]:
    """Write records to TSV file with sanitized fields. Optionally backup first."""
    backup_path = None
    if backup_dir:
        backup_path = backup_file(output_path, backup_dir)
    
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, delimiter='\t', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(columns)
        for record in records:
            row = [sanitize_field(record.get(col)) for col in columns]
            writer.writerow(row)
    return len(records), backup_path


def has_ai_estimates(record: dict) -> bool:
    """Check if record has AI weight/dimension estimates."""
    return (
        record.get('ai_weight_kg') is not None and
        record.get('ai_width_cm') is not None and
        record.get('ai_depth_cm') is not None and
        record.get('ai_height_cm') is not None
    )


def split_by_duplicates(records: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Split records into unique (proper) and duplicated by thumbnail_urls.
    Returns (proper_records, duplicated_records)
    """
    url_groups = defaultdict(list)
    for record in records:
        urls = record.get('thumbnail_urls', '') or ''
        url_groups[urls].append(record)
    
    proper = []
    duplicated = []
    
    for urls, group in url_groups.items():
        if len(group) == 1:
            proper.append(group[0])
        else:
            # Keep first as proper, rest as duplicated
            proper.append(group[0])
            duplicated.extend(group[1:])
    
    return proper, duplicated


def generate_category_files(records: list[dict], columns: list[str], categories_dir: Path):
    """
    Generate category-specific TSV files based on error rate thresholds.
    
    Categories are filtered by weight_error >= +50% (overestimate) or <= -50% (underestimate).
    """
    # Filter records that can be analyzed (have both ai_weight_kg and actual_weight)
    valid_records = [
        r for r in records 
        if r.get('ai_weight_kg') is not None and r.get('actual_weight') is not None
    ]
    
    # Category definitions: (filename, category_substring, error_type)
    # error_type: 'over' for +50% or more, 'under' for -50% or less
    category_defs = [
        # 과대추정 TOP 5
        ('o01_보이그룹_인형피규어_err50.tsv', '스타굿즈 > 보이그룹 > 인형/피규어', 'over'),
        ('o02_방송예능_인형피규어_err50.tsv', '스타굿즈 > 방송/예능/캐릭터 > 인형/피규어', 'over'),
        ('o03_바인더_err50.tsv', '바인더', 'over'),
        ('o04_키덜트_피규어인형_err50.tsv', '키덜트 > 피규어/인형', 'over'),
        ('o05_토트백_err50.tsv', '토트백', 'over'),
        # 과소추정 TOP 5
        ('u01_이어폰팁_err50.tsv', '이어폰/헤드폰액세서리', 'under'),
        ('u02_볼링가방_err50.tsv', '볼링가방', 'under'),
        ('u03_스킨토너_err50.tsv', '스킨/토너', 'under'),
        ('u04_에센스_err50.tsv', '에센스', 'under'),
        ('u05_시리얼_err50.tsv', '시리얼', 'under'),
    ]
    
    print("\n--- categories/ directory ---")
    
    for filename, cat_substr, error_type in category_defs:
        # Filter by category
        cat_records = [
            r for r in valid_records 
            if cat_substr in (r.get('category') or '')
        ]
        
        if not cat_records:
            print(f"  {filename}: 0 records (category not found)")
            continue
        
        # All records in category (not filtered by error threshold)
        # The category files contain ALL records for that category, not just error ones
        output_path = categories_dir / filename
        count, _ = write_tsv(cat_records, columns, output_path)
        
        # Calculate error stats
        over_50 = sum(1 for r in cat_records if (r.get('weight_error') or 0) >= 0.5)
        under_50 = sum(1 for r in cat_records if (r.get('weight_error') or 0) <= -0.5)
        
        print(f"  {filename}: {count} records (over:{over_50}, under:{under_50})")
    
    return


def main():
    """Main entry point."""
    project_root = get_project_root()
    
    # Paths
    jsonl_path = project_root / '.local' / 'basedata' / 'single_item_kse_full_20260203.jsonl'
    inputs_dir = project_root / 'inputs'
    backup_dir = inputs_dir / 'backups'
    
    print("=" * 60)
    print("Regenerate Derived Datasets from JSONL")
    print("=" * 60)
    
    # Check source exists
    if not jsonl_path.exists():
        print(f"ERROR: JSONL file not found: {jsonl_path}")
        return 1
    
    # Read source
    print(f"\nReading JSONL from: {jsonl_path}")
    all_records = read_jsonl(jsonl_path)
    print(f"  Total records: {len(all_records):,}")
    
    # Get columns from first record
    columns = list(all_records[0].keys())
    print(f"  Columns: {len(columns)}")
    
    # Create backup directory
    print(f"\nBackups will be saved to: {backup_dir}")
    
    # 1. datasource.tsv (already done, but ensure consistency)
    print("\n--- datasource.tsv ---")
    count, bak = write_tsv(all_records, columns, inputs_dir / 'datasource.tsv', backup_dir)
    print(f"  Written: {count:,} records" + (f" (backup: {bak.name})" if bak else ""))
    
    # 2. Split into proper and duplicated
    print("\n--- Splitting by duplicates (thumbnail_urls) ---")
    proper_records, duplicated_records = split_by_duplicates(all_records)
    print(f"  Proper (unique): {len(proper_records):,}")
    print(f"  Duplicated: {len(duplicated_records):,}")
    
    # 3. dataset_proper.tsv
    print("\n--- dataset_proper.tsv ---")
    count, bak = write_tsv(proper_records, columns, inputs_dir / 'dataset_proper.tsv', backup_dir)
    print(f"  Written: {count:,} records" + (f" (backup: {bak.name})" if bak else ""))
    
    # 4. dataset_duplicated.tsv
    print("\n--- dataset_duplicated.tsv ---")
    count, bak = write_tsv(duplicated_records, columns, inputs_dir / 'dataset_duplicated.tsv', backup_dir)
    print(f"  Written: {count:,} records" + (f" (backup: {bak.name})" if bak else ""))
    
    # 5. datasource_complete.tsv (has AI estimates)
    print("\n--- datasource_complete.tsv ---")
    complete_records = [r for r in all_records if has_ai_estimates(r)]
    count, bak = write_tsv(complete_records, columns, inputs_dir / 'datasource_complete.tsv', backup_dir)
    print(f"  Written: {count:,} records (has AI estimates)" + (f" (backup: {bak.name})" if bak else ""))
    
    # 6. datasource_incomplete.tsv (missing AI estimates)
    print("\n--- datasource_incomplete.tsv ---")
    incomplete_records = [r for r in all_records if not has_ai_estimates(r)]
    count, bak = write_tsv(incomplete_records, columns, inputs_dir / 'datasource_incomplete.tsv', backup_dir)
    print(f"  Written: {count:,} records (missing AI estimates)" + (f" (backup: {bak.name})" if bak else ""))
    
    # 7. missing_estimations.tsv (has actual weight but no AI estimates)
    print("\n--- missing_estimations.tsv ---")
    missing_records = [
        r for r in all_records 
        if not has_ai_estimates(r) and r.get('actual_weight') is not None
    ]
    count, bak = write_tsv(missing_records, columns, inputs_dir / 'missing_estimations.tsv', backup_dir)
    print(f"  Written: {count:,} records (has actual, missing AI)" + (f" (backup: {bak.name})" if bak else ""))
    
    # Summary
    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"  datasource.tsv:          {len(all_records):,}")
    print(f"  dataset_proper.tsv:      {len(proper_records):,}")
    print(f"  dataset_duplicated.tsv:  {len(duplicated_records):,}")
    print(f"  datasource_complete.tsv: {len(complete_records):,}")
    print(f"  datasource_incomplete.tsv: {len(incomplete_records):,}")
    print(f"  missing_estimations.tsv: {len(missing_records):,}")
    # 8. categories/ directory
    categories_dir = inputs_dir / 'categories'
    generate_category_files(all_records, columns, categories_dir)
    
    print()
    print("Done!")
    
    return 0


if __name__ == '__main__':
    exit(main())
