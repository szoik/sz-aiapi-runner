#!/usr/bin/env python3
import csv

filename = '20260128_experiment_datasource.tsv'

# Check rows where ai_weight_kg is missing
missing_ai_weight = []
missing_ai_dims = []
total = 0

with open(filename, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f, delimiter='\t')
    
    for row in reader:
        total += 1
        
        ai_weight = row.get('ai_weight_kg', '').strip()
        ai_w = row.get('ai_width_cm', '').strip()
        ai_d = row.get('ai_depth_cm', '').strip()
        ai_h = row.get('ai_height_cm', '').strip()
        
        # Check if AI weight is missing
        if not ai_weight or ai_weight.lower() in ('nan', 'none', 'null'):
            missing_ai_weight.append(row)
        
        # Check if AI dimensions are missing
        if not ai_w or not ai_d or not ai_h:
            missing_ai_dims.append(row)

print(f"Total rows: {total:,}")
print(f"Missing ai_weight_kg: {len(missing_ai_weight):,}")
print(f"Missing ai dimensions: {len(missing_ai_dims):,}")

# Check what data exists for rows with missing AI weight
print("\n" + "=" * 60)
print("SAMPLE ROWS WITH MISSING AI WEIGHT (first 5):")
print("=" * 60)

for i, row in enumerate(missing_ai_weight[:5]):
    print(f"\nRow {i+1}:")
    print(f"  product_version_id: {row.get('product_version_id', '')[:30]}...")
    print(f"  ai_weight_kg: '{row.get('ai_weight_kg', '')}'")
    print(f"  ai_width_cm: '{row.get('ai_width_cm', '')}'")
    print(f"  ai_depth_cm: '{row.get('ai_depth_cm', '')}'")
    print(f"  ai_height_cm: '{row.get('ai_height_cm', '')}'")
    print(f"  ai_volume_str: '{row.get('ai_volume_str', '')}'")
    print(f"  actual_weight: '{row.get('actual_weight', '')}'")
    print(f"  category: '{row.get('category', '')[:50]}...'")

# Check if there's any pattern - are these rows missing ALL AI data?
print("\n" + "=" * 60)
print("PATTERN ANALYSIS:")
print("=" * 60)

all_ai_missing = 0
partial_ai_missing = 0

for row in missing_ai_weight:
    ai_w = row.get('ai_width_cm', '').strip()
    ai_d = row.get('ai_depth_cm', '').strip()
    ai_h = row.get('ai_height_cm', '').strip()
    
    all_empty = all(not x or x.lower() in ('nan', 'none', 'null', '') for x in [ai_w, ai_d, ai_h])
    
    if all_empty:
        all_ai_missing += 1
    else:
        partial_ai_missing += 1

print(f"Rows with ALL AI data missing (weight + dims): {all_ai_missing}")
print(f"Rows with only weight missing (dims exist): {partial_ai_missing}")
