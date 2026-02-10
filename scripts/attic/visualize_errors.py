#!/usr/bin/env python3
"""
Visualize weight and volume error distribution.

Usage:
    python scripts/attic/visualize_errors.py \\
        -i colab/20260128_experiment_datasource.tsv \\
        -o .local/tmp/error_distribution.png
"""

import argparse
import csv
import matplotlib.pyplot as plt
import numpy as np


def load_data(filepath):
    data = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            data.append(row)
    return data

def parse_float(val):
    try:
        return float(val.strip()) if val and val.strip() else None
    except:
        return None

def main():
    parser = argparse.ArgumentParser(
        description="Visualize weight and volume error distribution",
        epilog="예시: python scripts/attic/visualize_errors.py -i colab/20260128_experiment_datasource.tsv -o .local/tmp/error_distribution.png"
    )
    parser.add_argument("-i", "--input", required=True, help="입력 TSV 파일 (weight_error, volume_error 컬럼 필요)")
    parser.add_argument("-o", "--output", required=True, help="출력 이미지 파일")
    args = parser.parse_args()

    data = load_data(args.input)
    
    weight_errors = [parse_float(r['weight_error']) for r in data]
    volume_errors = [parse_float(r['volume_error']) for r in data]
    
    weight_errors = [e for e in weight_errors if e is not None]
    volume_errors = [e for e in volume_errors if e is not None]
    
    print(f"Total rows: {len(data)}")
    print(f"Weight errors: {len(weight_errors)}")
    print(f"Volume errors: {len(volume_errors)}")
    
    # Stats
    print("\n=== Weight Error Stats ===")
    print(f"  Min: {min(weight_errors):.4f}")
    print(f"  Max: {max(weight_errors):.4f}")
    print(f"  Median: {np.median(weight_errors):.4f}")
    print(f"  Mean: {np.mean(weight_errors):.4f}")
    
    print("\n=== Volume Error Stats ===")
    print(f"  Min: {min(volume_errors):.4f}")
    print(f"  Max: {max(volume_errors):.4f}")
    print(f"  Median: {np.median(volume_errors):.4f}")
    print(f"  Mean: {np.mean(volume_errors):.4f}")
    
    # Create figure
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # Weight error histogram
    axes[0, 0].hist(weight_errors, bins=50, edgecolor='black', alpha=0.7)
    axes[0, 0].axvline(0, color='red', linestyle='--', label='Zero error')
    axes[0, 0].axvline(np.median(weight_errors), color='green', linestyle='--', label=f'Median: {np.median(weight_errors):.2f}')
    axes[0, 0].set_title('Weight Error Distribution')
    axes[0, 0].set_xlabel('Error (negative=underestimate, positive=overestimate)')
    axes[0, 0].set_ylabel('Count')
    axes[0, 0].legend()
    
    # Volume error histogram
    axes[0, 1].hist(volume_errors, bins=50, edgecolor='black', alpha=0.7, color='orange')
    axes[0, 1].axvline(0, color='red', linestyle='--', label='Zero error')
    axes[0, 1].axvline(np.median(volume_errors), color='green', linestyle='--', label=f'Median: {np.median(volume_errors):.2f}')
    axes[0, 1].set_title('Volume Error Distribution')
    axes[0, 1].set_xlabel('Error (negative=underestimate, positive=overestimate)')
    axes[0, 1].set_ylabel('Count')
    axes[0, 1].legend()
    
    # Weight error boxplot (clipped)
    weight_clipped = [e for e in weight_errors if -2 <= e <= 2]
    axes[1, 0].boxplot(weight_clipped, vert=True)
    axes[1, 0].set_title(f'Weight Error Boxplot (clipped ±2, n={len(weight_clipped)})')
    axes[1, 0].set_ylabel('Error')
    
    # Volume error boxplot (clipped)
    volume_clipped = [e for e in volume_errors if -2 <= e <= 2]
    axes[1, 1].boxplot(volume_clipped, vert=True)
    axes[1, 1].set_title(f'Volume Error Boxplot (clipped ±2, n={len(volume_clipped)})')
    axes[1, 1].set_ylabel('Error')
    
    plt.tight_layout()
    
    plt.savefig(args.output, dpi=150)
    print(f"\nSaved to: {args.output}")
    
    # Show if possible
    plt.show()

if __name__ == '__main__':
    main()
