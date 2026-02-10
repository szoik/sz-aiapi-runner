#!/usr/bin/env python3
"""
Analyze errors by actual weight range.

Usage:
    python scripts/attic/analyze_by_actual_weight.py -i inputs/datasource_complete.tsv
"""

import argparse
import csv
from collections import defaultdict

DEFAULT_INPUT = "inputs/datasource_complete.tsv"


def main():
    parser = argparse.ArgumentParser(description="실제 무게 구간별 오류 분석")
    parser.add_argument("-i", "--input", default=DEFAULT_INPUT, help="입력 TSV 파일")
    args = parser.parse_args()

    weight_ranges = [
        (0, 0.1),
        (0.1, 0.3),
        (0.3, 0.5),
        (0.5, 1.0),
        (1.0, 2.0),
        (2.0, 5.0),
        (5.0, float('inf'))
    ]
    
    range_data = defaultdict(list)
    
    with open(args.input, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        
        for row in reader:
            try:
                actual = float(row.get("actual_weight", 0) or 0)
                ai = float(row.get("ai_weight_kg", 0) or 0)
                
                if actual <= 0 or ai <= 0:
                    continue
                
                # Find range based on ACTUAL weight
                for low, high in weight_ranges:
                    if low <= actual < high:
                        range_data[(low, high)].append((actual, ai))
                        break
                        
            except (ValueError, KeyError):
                continue
    
    print("=== 실제 무게 구간별 AI 추정 분석 ===\n")
    print(f"{'구간':<15} {'개수':>8} {'평균실제':>10} {'평균AI':>10} {'AI/실제':>10} {'MAE':>10}")
    print("-" * 75)
    
    for (low, high), data in sorted(range_data.items()):
        if not data:
            continue
            
        n = len(data)
        avg_actual = sum(d[0] for d in data) / n
        avg_ai = sum(d[1] for d in data) / n
        ratio = avg_ai / avg_actual if avg_actual > 0 else 0
        
        errors = [abs(d[1] - d[0]) / d[0] for d in data if d[0] > 0]
        mae = sum(errors) / len(errors) * 100 if errors else 0
        
        range_str = f"{low}-{high}kg" if high != float('inf') else f"{low}kg+"
        print(f"{range_str:<15} {n:>8} {avg_actual:>10.3f} {avg_ai:>10.3f} {ratio:>10.2f} {mae:>9.1f}%")


if __name__ == "__main__":
    main()
