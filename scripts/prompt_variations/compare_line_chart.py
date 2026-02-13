#!/usr/bin/env python3
"""
Compare Line Chart Script

Generate line/area charts comparing old vs new estimation errors.

Output: line_chart_original.png, line_chart_sorted.png in the same directory as comparison.tsv

Usage:
    uv run python scripts/prompt_variations/compare_line_chart.py \
        -i .local/prompt_results/weight-volume.v2.system/u01_이어폰팁/comparison.tsv

    # With custom title
    uv run python scripts/prompt_variations/compare_line_chart.py \
        -i .local/prompt_results/.../comparison.tsv \
        -t "이어폰팁 카테고리"

    # Batch
    find .local/prompt_results -name "comparison.tsv" | while read f; do
        uv run python scripts/prompt_variations/compare_line_chart.py -i "$f"
    done
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np


def setup_korean_font():
    """Setup Korean font for matplotlib."""
    font_paths = [
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    ]
    for path in font_paths:
        if Path(path).exists():
            fm.fontManager.addfont(path)
            plt.rcParams["font.family"] = fm.FontProperties(fname=path).get_name()
            break
    plt.rcParams["axes.unicode_minus"] = False


def safe_float(value: str, default: float = 0.0) -> float:
    """Safely convert string to float."""
    try:
        return float(value) if value else default
    except (ValueError, TypeError):
        return default


def load_comparison_data(file_path: str) -> list[dict]:
    """Load comparison TSV file."""
    data = []
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            data.append(row)
    return data


def sort_dimensions(d1: float, d2: float, d3: float) -> tuple[float, float, float]:
    """Sort dimensions into (max, mid, min)."""
    dims = sorted([d1, d2, d3], reverse=True)
    return dims[0], dims[1], dims[2]


def calculate_dimension_errors(data: list[dict]) -> dict:
    """Calculate dimension errors (max, mid, min) for old and new prompts."""
    results = {
        "old_max": [], "old_mid": [], "old_min": [],
        "new_max": [], "new_mid": [], "new_min": [],
    }
    
    for d in data:
        # Actual dimensions
        actual_d1 = safe_float(d.get("actual_d1", 0))
        actual_d2 = safe_float(d.get("actual_d2", 0))
        actual_d3 = safe_float(d.get("actual_d3", 0))
        
        if actual_d1 <= 0 or actual_d2 <= 0 or actual_d3 <= 0:
            # Append 0 to keep alignment
            for key in results:
                results[key].append(0)
            continue
        
        actual_max, actual_mid, actual_min = sort_dimensions(actual_d1, actual_d2, actual_d3)
        
        # Old prompt dimensions
        old_w = safe_float(d.get("old_width_cm", 0))
        old_d = safe_float(d.get("old_depth_cm", 0))
        old_h = safe_float(d.get("old_height_cm", 0))
        
        if old_w > 0 and old_d > 0 and old_h > 0:
            old_max, old_mid, old_min = sort_dimensions(old_w, old_d, old_h)
            results["old_max"].append((old_max - actual_max) / actual_max)
            results["old_mid"].append((old_mid - actual_mid) / actual_mid)
            results["old_min"].append((old_min - actual_min) / actual_min)
        else:
            results["old_max"].append(0)
            results["old_mid"].append(0)
            results["old_min"].append(0)
        
        # New prompt dimensions
        new_w = safe_float(d.get("new_width_cm", 0))
        new_d = safe_float(d.get("new_depth_cm", 0))
        new_h = safe_float(d.get("new_height_cm", 0))
        
        if new_w > 0 and new_d > 0 and new_h > 0:
            new_max, new_mid, new_min = sort_dimensions(new_w, new_d, new_h)
            results["new_max"].append((new_max - actual_max) / actual_max)
            results["new_mid"].append((new_mid - actual_mid) / actual_mid)
            results["new_min"].append((new_min - actual_min) / actual_min)
        else:
            results["new_max"].append(0)
            results["new_mid"].append(0)
            results["new_min"].append(0)
    
    return results


def plot_line_chart(
    old_errors: list[float],
    new_errors: list[float],
    output_path: str,
    title: str = "",
    subtitle: str = "",
):
    """Generate line/area chart comparing old vs new errors."""
    setup_korean_font()
    
    n = len(old_errors)
    x = np.arange(n)
    
    fig, ax = plt.subplots(figsize=(16, 5))
    
    # Plot as area charts with transparency
    ax.fill_between(x, old_errors, alpha=0.4, color='red', label='기존 추정 오차율')
    ax.fill_between(x, new_errors, alpha=0.4, color='blue', label='신규 추정 오차율')
    
    # Plot lines on top
    ax.plot(x, old_errors, color='red', linewidth=0.8, alpha=0.8)
    ax.plot(x, new_errors, color='blue', linewidth=0.8, alpha=0.8)
    
    # Reference line at 0
    ax.axhline(y=0, color='gray', linestyle='-', linewidth=0.5, alpha=0.5)
    
    # Labels
    ax.set_xlabel('상품 순서')
    ax.set_ylabel('오차율 (%)')
    
    full_title = title if title else "기존 vs 신규 추정 오차율 비교"
    if subtitle:
        full_title += f" ({subtitle})"
    ax.set_title(full_title)
    
    ax.legend(loc='upper right')
    
    # Convert to percentage for y-axis
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y*100:.0f}%'))
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Saved: {output_path}")


def run_comparison(
    input_file: str,
    output_dir: str,
    title: str = "",
):
    """Run line chart comparison for all 5 metrics."""
    
    print(f"Input: {input_file}")
    print("-" * 80)
    
    # Load data
    data = load_comparison_data(input_file)
    print(f"Loaded {len(data)} records")
    
    if len(data) == 0:
        print("No data!")
        return 0
    
    # Calculate dimension errors
    dim_errors = calculate_dimension_errors(data)
    
    # Define all metrics: (old_errors, new_errors, metric_name, filename_prefix)
    metrics = [
        ([safe_float(d["old_weight_error"]) for d in data],
         [safe_float(d["new_weight_error"]) for d in data],
         "무게", "weight"),
        ([safe_float(d["old_volume_error"]) for d in data],
         [safe_float(d["new_volume_error"]) for d in data],
         "부피", "volume"),
        (dim_errors["old_max"], dim_errors["new_max"], "Max 치수", "dim_max"),
        (dim_errors["old_mid"], dim_errors["new_mid"], "Mid 치수", "dim_mid"),
        (dim_errors["old_min"], dim_errors["new_min"], "Min 치수", "dim_min"),
    ]
    
    # Ensure output directory exists
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    for old_errors, new_errors, metric_name, file_prefix in metrics:
        metric_title = f"{title} - {metric_name}" if title else metric_name
        
        # 1. Original order
        plot_line_chart(
            old_errors,
            new_errors,
            f"{output_dir}/line_chart_{file_prefix}_original.png",
            title=metric_title,
            subtitle="원본 순서",
        )
        
        # 2. Sorted by old error (descending: + → 0 → -)
        sorted_indices = sorted(range(len(old_errors)), key=lambda i: old_errors[i], reverse=True)
        old_errors_sorted = [old_errors[i] for i in sorted_indices]
        new_errors_sorted = [new_errors[i] for i in sorted_indices]
        
        plot_line_chart(
            old_errors_sorted,
            new_errors_sorted,
            f"{output_dir}/line_chart_{file_prefix}_sorted.png",
            title=metric_title,
            subtitle="기존 오차 큰 순",
        )
        
        # Print summary for this metric
        old_mae = np.mean([abs(e) for e in old_errors])
        new_mae = np.mean([abs(e) for e in new_errors])
        improved = sum(1 for o, n in zip(old_errors, new_errors) if abs(n) < abs(o))
        print(f"{metric_name}: MAE {old_mae*100:.1f}% → {new_mae*100:.1f}%, Improved {improved}/{len(data)}")
    
    return len(data)


def main():
    parser = argparse.ArgumentParser(
        description="Generate line chart comparison of old vs new estimation errors"
    )
    parser.add_argument("-i", "--input", required=True,
                        help="Comparison TSV file from merge_results.py")
    parser.add_argument("-o", "--output",
                        help="Output directory (default: same as input)")
    parser.add_argument("-t", "--title", default="",
                        help="Title for the charts")
    
    args = parser.parse_args()
    
    # Default output: same directory as input
    if args.output:
        output_dir = args.output
    else:
        output_dir = str(Path(args.input).parent)
    
    count = run_comparison(
        input_file=args.input,
        output_dir=output_dir,
        title=args.title,
    )
    
    if count > 0:
        print()
        print("Pipeline complete!")
        print(f"Results saved to: {output_dir}/")
    
    sys.exit(0 if count > 0 else 1)


if __name__ == "__main__":
    main()
