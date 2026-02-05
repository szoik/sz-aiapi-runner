#!/usr/bin/env python3
"""Apply weight correction factor based on AI estimated weight range."""

import argparse
import csv
import sys
from pathlib import Path


def get_correction_factor(ai_weight: float) -> float:
    """Get correction factor based on AI estimated weight."""
    if ai_weight < 0.1:
        return 1.0
    elif ai_weight < 0.3:
        return 1.2
    elif ai_weight < 0.5:
        return 1.3
    elif ai_weight < 1.0:
        return 1.5
    elif ai_weight < 2.0:
        return 2.0
    else:
        return 2.5


def calculate_error(actual: float, estimated: float) -> float:
    """Calculate relative error."""
    if actual == 0:
        return 0
    return (estimated - actual) / actual


def main():
    parser = argparse.ArgumentParser(description="Apply weight correction and compare")
    parser.add_argument("-i", "--input", required=True, help="Input datasource TSV")
    parser.add_argument("-o", "--output", help="Output TSV with corrected values")
    args = parser.parse_args()
    
    results = []
    
    with open(args.input, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        fieldnames = reader.fieldnames
        
        total = 0
        original_errors = []
        corrected_errors = []
        improved = 0
        
        for row in reader:
            try:
                actual_weight = float(row.get("actual_weight", 0) or 0)
                ai_weight = float(row.get("ai_weight_kg", 0) or 0)
                
                if actual_weight <= 0 or ai_weight <= 0:
                    continue
                
                total += 1
                
                # Original error
                original_error = calculate_error(actual_weight, ai_weight)
                original_errors.append(abs(original_error))
                
                # Corrected weight
                factor = get_correction_factor(ai_weight)
                corrected_weight = ai_weight * factor
                corrected_error = calculate_error(actual_weight, corrected_weight)
                corrected_errors.append(abs(corrected_error))
                
                if abs(corrected_error) < abs(original_error):
                    improved += 1
                
                # Store result
                row["corrected_weight"] = f"{corrected_weight:.3f}"
                row["correction_factor"] = f"{factor:.1f}"
                row["original_error"] = f"{original_error:.4f}"
                row["corrected_error"] = f"{corrected_error:.4f}"
                results.append(row)
                
            except (ValueError, KeyError) as e:
                continue
        
        # Summary
        original_mae = sum(original_errors) / len(original_errors) * 100 if original_errors else 0
        corrected_mae = sum(corrected_errors) / len(corrected_errors) * 100 if corrected_errors else 0
        
        print(f"Total records: {total}")
        print(f"Original MAE: {original_mae:.1f}%")
        print(f"Corrected MAE: {corrected_mae:.1f}%")
        print(f"Improved: {improved}/{total} ({improved/total*100:.1f}%)")
        print(f"Change: {original_mae:.1f}% → {corrected_mae:.1f}% ({corrected_mae - original_mae:+.1f}%)")
    
    # Write output if specified
    if args.output and results:
        output_fields = fieldnames + ["corrected_weight", "correction_factor", "original_error", "corrected_error"]
        with open(args.output, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=output_fields, delimiter="\t")
            writer.writeheader()
            writer.writerows(results)
        print(f"\nOutput saved: {args.output}")


if __name__ == "__main__":
    main()
