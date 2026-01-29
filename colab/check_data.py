#!/usr/bin/env python3
import csv
from collections import defaultdict

# Read TSV file
filename = '20260128_experiment_datasource.tsv'

# Track counts
counts = defaultdict(lambda: {'valid': 0, 'missing': 0})
total_rows = 0

# Columns to check
actual_cols = ['actual_weight', 'actual_d1', 'actual_d2', 'actual_d3', 'actual_max', 'actual_mid', 'actual_min']
ai_cols = ['ai_weight_kg', 'ai_width_cm', 'ai_depth_cm', 'ai_height_cm', 'ai_max', 'ai_mid', 'ai_min']
error_cols = ['weight_error', 'volume_error', 'max_error', 'mid_error', 'min_error']
all_cols = actual_cols + ai_cols + error_cols

# Combined checks
both_weight_count = 0
both_dims_count = 0
both_errors_count = 0
complete_data_count = 0

with open(filename, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f, delimiter='\t')
    
    for row in reader:
        total_rows += 1
        
        # Count valid/missing for each column
        for col in all_cols:
            val = row.get(col, '').strip()
            if val and val.lower() not in ('', 'nan', 'none', 'null'):
                counts[col]['valid'] += 1
            else:
                counts[col]['missing'] += 1
        
        # Combined checks
        actual_weight_ok = row.get('actual_weight', '').strip() not in ('', 'nan', 'none', 'null')
        ai_weight_ok = row.get('ai_weight_kg', '').strip() not in ('', 'nan', 'none', 'null')
        
        actual_dims_ok = all(
            row.get(col, '').strip() not in ('', 'nan', 'none', 'null') 
            for col in ['actual_d1', 'actual_d2', 'actual_d3']
        )
        ai_dims_ok = all(
            row.get(col, '').strip() not in ('', 'nan', 'none', 'null')
            for col in ['ai_width_cm', 'ai_depth_cm', 'ai_height_cm']
        )
        
        weight_error_ok = row.get('weight_error', '').strip() not in ('', 'nan', 'none', 'null')
        volume_error_ok = row.get('volume_error', '').strip() not in ('', 'nan', 'none', 'null')
        
        if actual_weight_ok and ai_weight_ok:
            both_weight_count += 1
        if actual_dims_ok and ai_dims_ok:
            both_dims_count += 1
        if weight_error_ok and volume_error_ok:
            both_errors_count += 1
        if actual_weight_ok and ai_weight_ok and actual_dims_ok and ai_dims_ok:
            complete_data_count += 1

# Print results
print(f'Total rows: {total_rows:,}')
print()

print('=' * 70)
print('ACTUAL VALUES (Ground Truth)')
print('=' * 70)
for col in actual_cols:
    valid = counts[col]['valid']
    missing = counts[col]['missing']
    pct = missing / total_rows * 100
    print(f'{col:20s}: {valid:6,} valid, {missing:6,} missing ({pct:.1f}%)')

print()
print('=' * 70)
print('AI ESTIMATED VALUES')
print('=' * 70)
for col in ai_cols:
    valid = counts[col]['valid']
    missing = counts[col]['missing']
    pct = missing / total_rows * 100
    print(f'{col:20s}: {valid:6,} valid, {missing:6,} missing ({pct:.1f}%)')

print()
print('=' * 70)
print('ERROR COLUMNS (Calculated)')
print('=' * 70)
for col in error_cols:
    valid = counts[col]['valid']
    missing = counts[col]['missing']
    pct = missing / total_rows * 100
    print(f'{col:20s}: {valid:6,} valid, {missing:6,} missing ({pct:.1f}%)')

print()
print('=' * 70)
print('COMBINED ANALYSIS')
print('=' * 70)
print(f'Both actual_weight AND ai_weight_kg exist: {both_weight_count:,}')
print(f'Both actual L,W,H AND ai L,W,H exist: {both_dims_count:,}')
print(f'Both weight_error AND volume_error exist: {both_errors_count:,}')
print(f'Complete data (weight + dimensions): {complete_data_count:,}')
