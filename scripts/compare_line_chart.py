#!/usr/bin/env python3
"""
Compare Line Chart Script

Generate line/area charts comparing old vs new estimation errors.

Output: line_chart_original.png, line_chart_sorted.png in the same directory as comparison.tsv

Usage:
    uv run python scripts/compare_line_chart.py \
        -i .local/prompt_results/weight-volume.v2.system/u01_이어폰팁/comparison.tsv

    # With custom title
    uv run python scripts/compare_line_chart.py \
        -i .local/prompt_results/.../comparison.tsv \
        -t "이어폰팁 카테고리"

    # Batch
    find .local/prompt_results -name "comparison.tsv" | while read f; do
        uv run python scripts/compare_line_chart.py -i "$f"
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
    """Run line chart comparison."""
    
    print(f"Input: {input_file}")
    print("-" * 80)
    
    # Load data
    data = load_comparison_data(input_file)
    print(f"Loaded {len(data)} records")
    
    if len(data) == 0:
        print("No data!")
        return 0
    
    # Extract error rates
    old_errors = [safe_float(d["old_weight_error"]) for d in data]
    new_errors = [safe_float(d["new_weight_error"]) for d in data]
    
    # Ensure output directory exists
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # 1. Original order
    plot_line_chart(
        old_errors,
        new_errors,
        f"{output_dir}/line_chart_original.png",
        title=title,
        subtitle="원본 순서",
    )
    
    # 2. Sorted by old error (descending: + → 0 → -)
    sorted_indices = sorted(range(len(old_errors)), key=lambda i: old_errors[i], reverse=True)
    old_errors_sorted = [old_errors[i] for i in sorted_indices]
    new_errors_sorted = [new_errors[i] for i in sorted_indices]
    
    plot_line_chart(
        old_errors_sorted,
        new_errors_sorted,
        f"{output_dir}/line_chart_sorted.png",
        title=title,
        subtitle="기존 오차 큰 순",
    )
    
    # Print summary
    old_mae = np.mean([abs(e) for e in old_errors])
    new_mae = np.mean([abs(e) for e in new_errors])
    improved = sum(1 for o, n in zip(old_errors, new_errors) if abs(n) < abs(o))
    
    print(f"\n=== Summary ===")
    print(f"MAE: {old_mae*100:.1f}% → {new_mae*100:.1f}%")
    print(f"Improved: {improved}/{len(data)} ({improved/len(data)*100:.1f}%)")
    
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
    
    sys.exit(0 if count > 0 else 1)


if __name__ == "__main__":
    main()
