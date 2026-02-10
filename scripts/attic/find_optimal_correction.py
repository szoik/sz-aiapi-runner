#!/usr/bin/env python3
"""
Find optimal correction factors by weight range.

Usage:
    python scripts/attic/find_optimal_correction.py -i inputs/datasource_complete.tsv
"""

import argparse
import csv
from collections import defaultdict

DEFAULT_INPUT = "inputs/datasource_complete.tsv"


def main():
    parser = argparse.ArgumentParser(description="최적 보정 계수 탐색")
    parser.add_argument("-i", "--input", default=DEFAULT_INPUT, help="입력 TSV 파일")
    args = parser.parse_args()

    weight_ranges = [
        (0, 0.1),
        (0.1, 0.3),
        (0.3, 0.5),
        (0.5, 1.0),
        (1.0, 2.0),
        (2.0, float('inf'))
    ]
    
    # Collect data by range
    range_data = defaultdict(list)
    
    with open(args.input, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        
        for row in reader:
            try:
                actual = float(row.get("actual_weight", 0) or 0)
                ai = float(row.get("ai_weight_kg", 0) or 0)
                
                if actual <= 0 or ai <= 0:
                    continue
                
                # Find range based on AI estimate
                for low, high in weight_ranges:
                    if low <= ai < high:
                        range_data[(low, high)].append((actual, ai))
                        break
                        
            except (ValueError, KeyError):
                continue
    
    print("=== AI 추정치 구간별 최적 보정계수 ===\n")
    print(f"{'구간':<15} {'개수':>8} {'평균 실제':>10} {'평균 AI':>10} {'최적계수':>10} {'현재오차':>10} {'보정후오차':>10}")
    print("-" * 85)
    
    optimal_factors = {}
    
    for (low, high), data in sorted(range_data.items()):
        if not data:
            continue
            
        n = len(data)
        avg_actual = sum(d[0] for d in data) / n
        avg_ai = sum(d[1] for d in data) / n
        
        # Optimal factor = average(actual / ai)
        ratios = [d[0] / d[1] for d in data if d[1] > 0]
        optimal = sum(ratios) / len(ratios) if ratios else 1.0
        
        # Current error (no correction)
        current_errors = [abs(d[1] - d[0]) / d[0] for d in data if d[0] > 0]
        current_mae = sum(current_errors) / len(current_errors) * 100 if current_errors else 0
        
        # Error after correction
        corrected_errors = [abs(d[1] * optimal - d[0]) / d[0] for d in data if d[0] > 0]
        corrected_mae = sum(corrected_errors) / len(corrected_errors) * 100 if corrected_errors else 0
        
        range_str = f"{low}-{high}kg" if high != float('inf') else f"{low}kg+"
        print(f"{range_str:<15} {n:>8} {avg_actual:>10.3f} {avg_ai:>10.3f} {optimal:>10.2f} {current_mae:>9.1f}% {corrected_mae:>9.1f}%")
        
        optimal_factors[(low, high)] = optimal
    
    print("\n=== 권장 보정계수 ===")
    for (low, high), factor in sorted(optimal_factors.items()):
        range_str = f"{low}-{high}kg" if high != float('inf') else f"{low}kg+"
        print(f"{range_str}: {factor:.2f}")


if __name__ == "__main__":
    main()
