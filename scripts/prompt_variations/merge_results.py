#!/usr/bin/env python3
"""
Merge Results Script

Join original datasource with new estimation results for comparison.
Calculates error rates for both old and new estimations.

Output: comparison.tsv in the same directory as result.tsv

Usage:
    # Merge (output to same directory as result.tsv)
    uv run python scripts/merge_results.py \
        -d inputs/datasource_complete.tsv \
        -r .local/prompt_results/weight-volume.v2.system/datasource_complete/result.tsv

    # Custom output path
    uv run python scripts/merge_results.py \
        -d inputs/datasource_complete.tsv \
        -r .local/prompt_results/.../result.tsv \
        -o custom/path/comparison.tsv

    # Batch merge
    find .local/prompt_results -name "result.tsv" | while read f; do
        uv run python scripts/merge_results.py \
            -d inputs/datasource_complete.tsv \
            -r "$f"
    done
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


def safe_float(value: str, default: float = 0.0) -> float:
    """Safely convert string to float."""
    try:
        return float(value) if value else default
    except (ValueError, TypeError):
        return default


def calculate_error(estimated: float, actual: float) -> float:
    """Calculate relative error: (estimated - actual) / actual."""
    if actual == 0:
        return 0.0
    return (estimated - actual) / actual


def load_tsv_as_dict(file_path: str, key_column: str) -> dict[str, dict]:
    """Load TSV file into dict keyed by specified column."""
    data = {}
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            key = row.get(key_column, "")
            if key:
                data[key] = row
    return data


def merge_and_compare(
    datasource_file: str,
    result_file: str,
    output_file: str,
) -> int:
    """Merge datasource with result and calculate comparison metrics."""
    
    # Load result file
    print(f"Loading result: {result_file}")
    result_data = load_tsv_as_dict(result_file, "order_id")
    print(f"  -> {len(result_data)} records")
    
    # Ensure output directory exists
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Output columns
    output_columns = [
        # ID
        "order_id",
        "title_origin",
        "category",
        # Actual values
        "actual_weight",
        "actual_d1",
        "actual_d2",
        "actual_d3",
        "actual_volume_cm3",
        # Old AI values
        "old_weight_kg",
        "old_width_cm",
        "old_depth_cm",
        "old_height_cm",
        "old_volume_cm3",
        # New AI values
        "new_weight_kg",
        "new_width_cm",
        "new_depth_cm",
        "new_height_cm",
        "new_volume_cm3",
        # Error rates
        "old_weight_error",
        "new_weight_error",
        "old_volume_error",
        "new_volume_error",
        # Improvement flags
        "weight_improved",
        "volume_improved",
        # Reason
        "new_reason",
    ]
    
    matched = 0
    
    print(f"Processing datasource: {datasource_file}")
    
    with open(output_file, "w", encoding="utf-8", newline="") as out_f:
        writer = csv.DictWriter(out_f, fieldnames=output_columns, delimiter="\t")
        writer.writeheader()
        
        with open(datasource_file, "r", encoding="utf-8") as ds_f:
            reader = csv.DictReader(ds_f, delimiter="\t")
            
            for row in reader:
                order_id = row.get("order_id", "")
                
                # Skip if no matching result
                if order_id not in result_data:
                    continue
                
                result = result_data[order_id]
                
                # Extract actual values
                actual_weight = safe_float(row.get("actual_weight", ""))
                actual_d1 = safe_float(row.get("actual_d1", ""))
                actual_d2 = safe_float(row.get("actual_d2", ""))
                actual_d3 = safe_float(row.get("actual_d3", ""))
                actual_volume = safe_float(row.get("actual_volume_cm3", ""))
                
                # Extract old AI values
                old_weight = safe_float(row.get("ai_weight_kg", ""))
                old_width = safe_float(row.get("ai_width_cm", ""))
                old_depth = safe_float(row.get("ai_depth_cm", ""))
                old_height = safe_float(row.get("ai_height_cm", ""))
                old_volume = safe_float(row.get("ai_volume_cm3", ""))
                
                # Extract new AI values
                new_weight = safe_float(result.get("new_weight_kg", ""))
                new_width = safe_float(result.get("new_width_cm", ""))
                new_depth = safe_float(result.get("new_depth_cm", ""))
                new_height = safe_float(result.get("new_height_cm", ""))
                new_volume = new_width * new_depth * new_height
                
                # Calculate errors
                old_weight_error = calculate_error(old_weight, actual_weight)
                new_weight_error = calculate_error(new_weight, actual_weight)
                old_volume_error = calculate_error(old_volume, actual_volume) if actual_volume > 0 else 0
                new_volume_error = calculate_error(new_volume, actual_volume) if actual_volume > 0 else 0
                
                # Improvement flags
                weight_improved = abs(new_weight_error) < abs(old_weight_error)
                volume_improved = abs(new_volume_error) < abs(old_volume_error)
                
                writer.writerow({
                    "order_id": order_id,
                    "title_origin": row.get("title_origin", ""),
                    "category": row.get("category", ""),
                    "actual_weight": actual_weight,
                    "actual_d1": actual_d1,
                    "actual_d2": actual_d2,
                    "actual_d3": actual_d3,
                    "actual_volume_cm3": actual_volume,
                    "old_weight_kg": old_weight,
                    "old_width_cm": old_width,
                    "old_depth_cm": old_depth,
                    "old_height_cm": old_height,
                    "old_volume_cm3": old_volume,
                    "new_weight_kg": new_weight,
                    "new_width_cm": new_width,
                    "new_depth_cm": new_depth,
                    "new_height_cm": new_height,
                    "new_volume_cm3": new_volume,
                    "old_weight_error": f"{old_weight_error:.4f}",
                    "new_weight_error": f"{new_weight_error:.4f}",
                    "old_volume_error": f"{old_volume_error:.4f}",
                    "new_volume_error": f"{new_volume_error:.4f}",
                    "weight_improved": "1" if weight_improved else "0",
                    "volume_improved": "1" if volume_improved else "0",
                    "new_reason": result.get("new_reason", ""),
                })
                
                matched += 1
    
    print(f"  -> {matched} records merged")
    print(f"Output saved: {output_file}")
    
    return matched


def main():
    parser = argparse.ArgumentParser(
        description="Merge datasource with new estimation results"
    )
    parser.add_argument("-d", "--datasource", required=True,
                        help="Original datasource TSV file")
    parser.add_argument("-r", "--result", required=True,
                        help="New estimation result TSV file")
    parser.add_argument("-o", "--output",
                        help="Output comparison TSV file (default: comparison.tsv in result directory)")
    
    args = parser.parse_args()
    
    # Default output: comparison.tsv in same directory as result.tsv
    if args.output:
        output_file = args.output
    else:
        result_path = Path(args.result)
        output_file = str(result_path.parent / "comparison.tsv")
    
    matched = merge_and_compare(
        datasource_file=args.datasource,
        result_file=args.result,
        output_file=output_file,
    )
    
    if matched > 0:
        print()
        print("Next step:")
        print(f"  uv run python scripts/compare_prompts.py \\")
        print(f"    -i {output_file}")
    
    sys.exit(0 if matched > 0 else 1)


if __name__ == "__main__":
    main()
