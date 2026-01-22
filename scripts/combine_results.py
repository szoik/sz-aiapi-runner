#!/usr/bin/env python3
"""
Combine sample200.tsv with result2.tsv to generate combined.tsv.

Joins by 'id' field and calculates error metrics.

Usage:
  python scripts/combine_results.py <sample.tsv> <result2.tsv> [output.tsv]

If output is not specified, writes to combined.tsv in the same directory as result2.tsv.
"""

import argparse
import csv
from pathlib import Path


def safe_float(val: str) -> float | None:
    """Convert string to float, return None if empty or invalid."""
    if not val or val.strip() == '':
        return None
    try:
        return float(val)
    except ValueError:
        return None


def calc_error(estimated: float | None, actual: float | None) -> str:
    """Calculate relative error: |estimated - actual| / actual"""
    if estimated is None or actual is None or actual == 0:
        return ''
    error = abs(estimated - actual) / actual
    return f'{error:.4f}'


def combine(source_path: Path, result_path: Path, output_path: Path) -> None:
    # Read source (sample200.tsv)
    source_data = {}
    with open(source_path, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            source_data[row['id']] = row
    
    # Read result2.tsv
    result_data = {}
    with open(result_path, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            if row.get('id'):  # skip blank lines
                result_data[row['id']] = row
    
    # Output header
    output_header = [
        'id', 'order_item_order_id', 'product_title_origin', 'product_category',
        'actual_weight_kg', 'actual_width_cm', 'actual_length_cm', 'actual_height_cm', 'actual_volume_m3',
        'ai_estimated_weight_kg', 'ai_estimated_width_cm', 'ai_estimated_length_cm', 'ai_estimated_height_cm', 'ai_calculated_volume_m3',
        'vw', 'vl', 'vh', 'vol', 'pvw', 'pvl', 'pvh', 'pvol', 'weight', 'reason',
        'cur_wt_error', 'cur_vol_error', 'exp_wt_error', 'exp_vol_error'
    ]
    
    rows = []
    # Inner join by id
    for id_val in source_data:
        if id_val not in result_data:
            continue
        
        src = source_data[id_val]
        res = result_data[id_val]
        
        # Parse values for error calculation
        actual_weight = safe_float(src.get('actual_weight_kg'))
        actual_volume = safe_float(src.get('actual_volume_m3'))
        ai_weight = safe_float(src.get('ai_estimated_weight_kg'))
        ai_volume = safe_float(src.get('ai_calculated_volume_m3'))
        exp_weight = safe_float(res.get('weight'))
        exp_volume = safe_float(res.get('vol'))
        
        row = {
            'id': id_val,
            'order_item_order_id': src.get('order_item_order_id', ''),
            'product_title_origin': src.get('product_title_origin', ''),
            'product_category': src.get('product_category', ''),
            'actual_weight_kg': src.get('actual_weight_kg', ''),
            'actual_width_cm': src.get('actual_width_cm', ''),
            'actual_length_cm': src.get('actual_length_cm', ''),
            'actual_height_cm': src.get('actual_height_cm', ''),
            'actual_volume_m3': src.get('actual_volume_m3', ''),
            'ai_estimated_weight_kg': src.get('ai_estimated_weight_kg', ''),
            'ai_estimated_width_cm': src.get('ai_estimated_width_cm', ''),
            'ai_estimated_length_cm': src.get('ai_estimated_length_cm', ''),
            'ai_estimated_height_cm': src.get('ai_estimated_height_cm', ''),
            'ai_calculated_volume_m3': src.get('ai_calculated_volume_m3', ''),
            'vw': res.get('vw', ''),
            'vl': res.get('vl', ''),
            'vh': res.get('vh', ''),
            'vol': res.get('vol', ''),
            'pvw': res.get('pvw', ''),
            'pvl': res.get('pvl', ''),
            'pvh': res.get('pvh', ''),
            'pvol': res.get('pvol', ''),
            'weight': res.get('weight', ''),
            'reason': res.get('reason', ''),
            'cur_wt_error': calc_error(ai_weight, actual_weight),
            'cur_vol_error': calc_error(ai_volume, actual_volume),
            'exp_wt_error': calc_error(exp_weight, actual_weight),
            'exp_vol_error': calc_error(exp_volume, actual_volume),
        }
        rows.append(row)
    
    with open(output_path, 'w') as f:
        writer = csv.DictWriter(f, fieldnames=output_header, delimiter='\t')
        writer.writeheader()
        writer.writerows(rows)
    
    print(f'Combined {len(rows)} rows -> {output_path}')


def main():
    parser = argparse.ArgumentParser(description='Combine sample TSV with result2.tsv')
    parser.add_argument('source', help='Source TSV file (sample200.tsv)')
    parser.add_argument('result', help='Result TSV file (result2.tsv)')
    parser.add_argument('output', nargs='?', help='Output TSV file (default: combined.tsv in same directory as result)')
    args = parser.parse_args()
    
    source_path = Path(args.source)
    result_path = Path(args.result)
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = result_path.parent / 'combined.tsv'
    
    combine(source_path, result_path, output_path)


if __name__ == '__main__':
    main()
