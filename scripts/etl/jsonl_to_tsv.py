#!/usr/bin/env python3
"""
Convert JSONL file to clean TSV file for datasource.

Usage:
    python scripts/etl/jsonl_to_tsv.py
"""

import json
import csv
import shutil
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from common import PROJECT_ROOT


def read_existing_tsv_header(tsv_path: Path) -> list[str]:
    """Read column headers from existing TSV file."""
    with open(tsv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        header = next(reader)
    return header


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
    """
    Sanitize a field value for TSV output.
    - Replace newlines with space
    - Replace tabs with space
    - Convert None to empty string
    """
    if value is None:
        return ''

    # Convert to string
    text = str(value)

    # Replace problematic characters
    text = text.replace('\n', ' ')
    text = text.replace('\r', ' ')
    text = text.replace('\t', ' ')

    # Collapse multiple spaces into one
    while '  ' in text:
        text = text.replace('  ', ' ')

    return text.strip()


def convert_jsonl_to_tsv(
    jsonl_path: Path,
    tsv_path: Path,
    backup: bool = True
) -> dict:
    """
    Convert JSONL to TSV with sanitized fields.

    Returns:
        dict with conversion statistics
    """
    stats = {
        'source_records': 0,
        'output_records': 0,
        'columns': 0,
        'backup_created': False,
        'backup_path': None
    }

    # Read existing TSV header
    print(f"Reading existing TSV header from: {tsv_path}")
    columns = read_existing_tsv_header(tsv_path)
    stats['columns'] = len(columns)
    print(f"  Found {len(columns)} columns")
    print(f"  Columns: {columns[:5]}... (showing first 5)")

    # Read JSONL records
    print(f"\nReading JSONL from: {jsonl_path}")
    records = read_jsonl(jsonl_path)
    stats['source_records'] = len(records)
    print(f"  Found {len(records):,} records")

    # Backup existing TSV
    if backup and tsv_path.exists():
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = tsv_path.parent / f"{tsv_path.stem}_backup_{timestamp}{tsv_path.suffix}"
        shutil.copy2(tsv_path, backup_path)
        stats['backup_created'] = True
        stats['backup_path'] = str(backup_path)
        print(f"\n  Backup created: {backup_path}")

    # Write new TSV
    print(f"\nWriting clean TSV to: {tsv_path}")
    with open(tsv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, delimiter='\t', quoting=csv.QUOTE_MINIMAL)

        # Write header
        writer.writerow(columns)

        # Write records
        for record in records:
            row = []
            for col in columns:
                value = record.get(col)
                sanitized = sanitize_field(value)
                row.append(sanitized)
            writer.writerow(row)
            stats['output_records'] += 1

    print(f"  Wrote {stats['output_records']:,} records")

    return stats


def main():
    """Main entry point."""
    # Paths
    jsonl_path = PROJECT_ROOT / '.local' / 'basedata' / 'single_item_kse_full_20260203.jsonl'
    tsv_path = PROJECT_ROOT / 'inputs' / 'datasource.tsv'

    print("=" * 60)
    print("JSONL to TSV Converter")
    print("=" * 60)

    # Check files exist
    if not jsonl_path.exists():
        print(f"ERROR: JSONL file not found: {jsonl_path}")
        return 1

    if not tsv_path.exists():
        print(f"ERROR: TSV file not found: {tsv_path}")
        return 1

    # Convert
    stats = convert_jsonl_to_tsv(jsonl_path, tsv_path, backup=True)

    print()
    print("=" * 60)
    print("Conversion Summary")
    print("=" * 60)
    print(f"  Source records:  {stats['source_records']:,}")
    print(f"  Output records:  {stats['output_records']:,}")
    print(f"  Columns:         {stats['columns']}")
    if stats['backup_created']:
        print(f"  Backup:          {stats['backup_path']}")
    print()
    print("Done!")

    return 0


if __name__ == '__main__':
    exit(main())
