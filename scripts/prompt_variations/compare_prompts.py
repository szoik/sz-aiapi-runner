#!/usr/bin/env python3
"""
Compare Prompts Visualization Script

Generate comparison graphs and statistics between old and new prompt results.

Output: comparison.png, scatter.png, stats.md in the same directory as comparison.tsv

Usage:
    # Generate visualization (output to same directory as comparison.tsv)
    uv run python scripts/prompt_variations/compare_prompts.py \
        -i .local/prompt_results/weight-volume.v2.system/full/20250202-143052/comparison.tsv

    # With custom title
    uv run python scripts/prompt_variations/compare_prompts.py \
        -i .local/prompt_results/.../comparison.tsv \
        -t "로봇완구 카테고리"

    # Custom output prefix
    uv run python scripts/prompt_variations/compare_prompts.py \
        -i .local/prompt_results/.../comparison.tsv \
        -o custom/path/prefix

    # Batch visualization
    find .local/prompt_results -name "comparison.tsv" | while read f; do
        uv run python scripts/prompt_variations/compare_prompts.py -i "$f"
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


# Korean font setup
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
    # New prompt errors
    new_max_errors = []
    new_mid_errors = []
    new_min_errors = []
    # Old prompt errors
    old_max_errors = []
    old_mid_errors = []
    old_min_errors = []
    
    for d in data:
        # Actual dimensions
        actual_d1 = safe_float(d.get("actual_d1", 0))
        actual_d2 = safe_float(d.get("actual_d2", 0))
        actual_d3 = safe_float(d.get("actual_d3", 0))
        
        # Old prompt dimensions
        old_w = safe_float(d.get("old_width_cm", 0))
        old_d = safe_float(d.get("old_depth_cm", 0))
        old_h = safe_float(d.get("old_height_cm", 0))
        
        # New prompt dimensions
        new_w = safe_float(d.get("new_width_cm", 0))
        new_d = safe_float(d.get("new_depth_cm", 0))
        new_h = safe_float(d.get("new_height_cm", 0))
        
        if actual_d1 <= 0 or actual_d2 <= 0 or actual_d3 <= 0:
            continue
        
        # Sort actual into max/mid/min
        actual_max, actual_mid, actual_min = sort_dimensions(actual_d1, actual_d2, actual_d3)
        
        # Old prompt errors
        if old_w > 0 and old_d > 0 and old_h > 0:
            old_max, old_mid, old_min = sort_dimensions(old_w, old_d, old_h)
            old_max_errors.append((old_max - actual_max) / actual_max)
            old_mid_errors.append((old_mid - actual_mid) / actual_mid)
            old_min_errors.append((old_min - actual_min) / actual_min)
        
        # New prompt errors
        if new_w > 0 and new_d > 0 and new_h > 0:
            new_max, new_mid, new_min = sort_dimensions(new_w, new_d, new_h)
            new_max_errors.append((new_max - actual_max) / actual_max)
            new_mid_errors.append((new_mid - actual_mid) / actual_mid)
            new_min_errors.append((new_min - actual_min) / actual_min)
    
    return {
        # New prompt
        "max_errors": new_max_errors,
        "mid_errors": new_mid_errors,
        "min_errors": new_min_errors,
        "max_mae": np.mean([abs(e) for e in new_max_errors]) if new_max_errors else 0,
        "mid_mae": np.mean([abs(e) for e in new_mid_errors]) if new_mid_errors else 0,
        "min_mae": np.mean([abs(e) for e in new_min_errors]) if new_min_errors else 0,
        # Old prompt
        "old_max_errors": old_max_errors,
        "old_mid_errors": old_mid_errors,
        "old_min_errors": old_min_errors,
        "old_max_mae": np.mean([abs(e) for e in old_max_errors]) if old_max_errors else 0,
        "old_mid_mae": np.mean([abs(e) for e in old_mid_errors]) if old_mid_errors else 0,
        "old_min_mae": np.mean([abs(e) for e in old_min_errors]) if old_min_errors else 0,
    }


def calculate_stats(data: list[dict]) -> dict:
    """Calculate comparison statistics."""
    n = len(data)
    if n == 0:
        return {}
    
    old_weight_errors = [abs(safe_float(d["old_weight_error"])) for d in data]
    new_weight_errors = [abs(safe_float(d["new_weight_error"])) for d in data]
    old_volume_errors = [abs(safe_float(d["old_volume_error"])) for d in data]
    new_volume_errors = [abs(safe_float(d["new_volume_error"])) for d in data]
    
    # Raw errors (not absolute) for distribution plots
    new_weight_errors_raw = [safe_float(d["new_weight_error"]) for d in data]
    new_volume_errors_raw = [safe_float(d["new_volume_error"]) for d in data]
    
    weight_improved = sum(1 for d in data if d.get("weight_improved") == "1")
    volume_improved = sum(1 for d in data if d.get("volume_improved") == "1")
    
    # Dimension errors
    dim_stats = calculate_dimension_errors(data)
    
    return {
        "count": n,
        "old_weight_mae": np.mean(old_weight_errors),
        "new_weight_mae": np.mean(new_weight_errors),
        "old_volume_mae": np.mean(old_volume_errors),
        "new_volume_mae": np.mean(new_volume_errors),
        "weight_improved_count": weight_improved,
        "weight_improved_pct": weight_improved / n * 100,
        "volume_improved_count": volume_improved,
        "volume_improved_pct": volume_improved / n * 100,
        "old_weight_errors": old_weight_errors,
        "new_weight_errors": new_weight_errors,
        "old_volume_errors": old_volume_errors,
        "new_volume_errors": new_volume_errors,
        "new_weight_errors_raw": new_weight_errors_raw,
        "new_volume_errors_raw": new_volume_errors_raw,
        # Dimension stats (new)
        "dim_max_errors": dim_stats["max_errors"],
        "dim_mid_errors": dim_stats["mid_errors"],
        "dim_min_errors": dim_stats["min_errors"],
        "dim_max_mae": dim_stats["max_mae"],
        "dim_mid_mae": dim_stats["mid_mae"],
        "dim_min_mae": dim_stats["min_mae"],
        # Dimension stats (old)
        "dim_old_max_errors": dim_stats["old_max_errors"],
        "dim_old_mid_errors": dim_stats["old_mid_errors"],
        "dim_old_min_errors": dim_stats["old_min_errors"],
        "dim_old_max_mae": dim_stats["old_max_mae"],
        "dim_old_mid_mae": dim_stats["old_mid_mae"],
        "dim_old_min_mae": dim_stats["old_min_mae"],
    }


def plot_error_comparison(
    data: list[dict],
    stats: dict,
    output_prefix: str,
    title: str = "",
):
    """Generate comparison plots."""
    setup_korean_font()
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f"프롬프트 비교: {title}" if title else "프롬프트 비교", fontsize=14, fontweight="bold")
    
    # 1. Weight Error Distribution (Box Plot)
    ax1 = axes[0, 0]
    box_data = [stats["old_weight_errors"], stats["new_weight_errors"]]
    bp = ax1.boxplot(box_data, labels=["기존 프롬프트", "개선 프롬프트"], patch_artist=True)
    bp["boxes"][0].set_facecolor("#ff9999")
    bp["boxes"][1].set_facecolor("#99ff99")
    ax1.set_ylabel("무게 오차율 (절대값)")
    ax1.set_title("무게 오차 분포")
    ax1.axhline(y=0.5, color="red", linestyle="--", alpha=0.5, label="±50% 기준선")
    ax1.legend()
    
    # 2. Volume Error Distribution (Box Plot)
    ax2 = axes[0, 1]
    box_data = [stats["old_volume_errors"], stats["new_volume_errors"]]
    bp = ax2.boxplot(box_data, labels=["기존 프롬프트", "개선 프롬프트"], patch_artist=True)
    bp["boxes"][0].set_facecolor("#ff9999")
    bp["boxes"][1].set_facecolor("#99ff99")
    ax2.set_ylabel("부피 오차율 (절대값)")
    ax2.set_title("부피 오차 분포")
    ax2.axhline(y=0.5, color="red", linestyle="--", alpha=0.5, label="±50% 기준선")
    ax2.legend()
    
    # 3. Improvement Summary (Bar Chart)
    ax3 = axes[1, 0]
    metrics = ["무게", "부피"]
    improved = [stats["weight_improved_pct"], stats["volume_improved_pct"]]
    not_improved = [100 - stats["weight_improved_pct"], 100 - stats["volume_improved_pct"]]
    
    x = np.arange(len(metrics))
    width = 0.35
    bars1 = ax3.bar(x - width/2, improved, width, label="개선됨", color="#99ff99")
    bars2 = ax3.bar(x + width/2, not_improved, width, label="개선 안됨", color="#ff9999")
    
    ax3.set_ylabel("비율 (%)")
    ax3.set_title("개선 비율")
    ax3.set_xticks(x)
    ax3.set_xticklabels(metrics)
    ax3.legend()
    ax3.set_ylim(0, 100)
    
    # Add value labels
    for bar in bars1:
        height = bar.get_height()
        ax3.annotate(f"{height:.1f}%", xy=(bar.get_x() + bar.get_width()/2, height),
                     ha="center", va="bottom", fontsize=10)
    
    # 4. MAE Comparison (Bar Chart)
    ax4 = axes[1, 1]
    metrics = ["무게 MAE", "부피 MAE"]
    old_values = [stats["old_weight_mae"] * 100, stats["old_volume_mae"] * 100]
    new_values = [stats["new_weight_mae"] * 100, stats["new_volume_mae"] * 100]
    
    x = np.arange(len(metrics))
    bars1 = ax4.bar(x - width/2, old_values, width, label="기존", color="#ff9999")
    bars2 = ax4.bar(x + width/2, new_values, width, label="개선", color="#99ff99")
    
    ax4.set_ylabel("평균 절대 오차율 (%)")
    ax4.set_title("평균 오차율 비교")
    ax4.set_xticks(x)
    ax4.set_xticklabels(metrics)
    ax4.legend()
    
    # Add value labels
    for bar in bars1 + bars2:
        height = bar.get_height()
        ax4.annotate(f"{height:.1f}%", xy=(bar.get_x() + bar.get_width()/2, height),
                     ha="center", va="bottom", fontsize=10)
    
    plt.tight_layout()
    
    # Save plot
    plot_path = f"{output_prefix}_comparison.png"
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Plot saved: {plot_path}")


def plot_error_distributions(
    stats: dict,
    output_prefix: str,
    title: str = "",
):
    """Generate error distribution histograms for all metrics (5 charts)."""
    setup_korean_font()
    
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle(f"오차 분포: {title}" if title else "오차 분포", fontsize=14, fontweight="bold")
    
    # Common histogram settings
    bins = np.linspace(-2, 2, 41)  # -200% to +200% in 10% bins
    
    metrics = [
        ("new_weight_errors_raw", "new_weight_mae", "무게", "#4a90d9"),
        ("new_volume_errors_raw", "new_volume_mae", "부피", "#4a90d9"),
        ("dim_max_errors", "dim_max_mae", "Max 치수", "#66b366"),
        ("dim_mid_errors", "dim_mid_mae", "Mid 치수", "#66b366"),
        ("dim_min_errors", "dim_min_mae", "Min 치수", "#66b366"),
    ]
    
    axes_flat = [axes[0, 0], axes[0, 1], axes[0, 2], axes[1, 0], axes[1, 1]]
    
    for ax, (errors_key, mae_key, label, color) in zip(axes_flat, metrics):
        errors = stats.get(errors_key, [])
        mae = stats.get(mae_key, 0)
        if errors:
            ax.hist(errors, bins=bins, color=color, edgecolor="white", alpha=0.8)
        ax.axvline(x=0, color="red", linestyle="--", alpha=0.7)
        ax.set_xlabel("오차율")
        ax.set_ylabel("빈도")
        ax.set_title(f"{label} 오차 분포 (MAE: {mae*100:.1f}%)")
        ax.set_xlim(-2, 2)
    
    # Hide unused subplot
    axes[1, 2].axis("off")
    
    plt.tight_layout()
    
    # Save plot
    plot_path = f"{output_prefix}_distributions.png"
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Distribution plot saved: {plot_path}")


def plot_scatter_comparison(
    data: list[dict],
    stats: dict,
    output_prefix: str,
    title: str = "",
):
    """Generate scatter plots comparing old vs new errors for all metrics."""
    setup_korean_font()
    
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle(f"오차 변화 (기존 vs 개선): {title}" if title else "오차 변화 (기존 vs 개선)", fontsize=14, fontweight="bold")
    
    # Define metrics: (old_errors, new_errors, title)
    metrics = [
        ([safe_float(d["old_weight_error"]) for d in data],
         [safe_float(d["new_weight_error"]) for d in data],
         "무게"),
        ([safe_float(d["old_volume_error"]) for d in data],
         [safe_float(d["new_volume_error"]) for d in data],
         "부피"),
        (stats["dim_old_max_errors"], stats["dim_max_errors"], "Max 치수"),
        (stats["dim_old_mid_errors"], stats["dim_mid_errors"], "Mid 치수"),
        (stats["dim_old_min_errors"], stats["dim_min_errors"], "Min 치수"),
    ]
    
    axes_flat = [axes[0, 0], axes[0, 1], axes[0, 2], axes[1, 0], axes[1, 1]]
    
    for ax, (old_errors, new_errors, metric_title) in zip(axes_flat, metrics):
        if not old_errors or not new_errors:
            ax.axis("off")
            continue
        
        # Ensure same length
        min_len = min(len(old_errors), len(new_errors))
        old_errors = old_errors[:min_len]
        new_errors = new_errors[:min_len]
        
        colors = ["green" if abs(new) < abs(old) else "red" 
                  for old, new in zip(old_errors, new_errors)]
        ax.scatter(old_errors, new_errors, c=colors, alpha=0.5, s=30)
        
        # Calculate limits
        all_errors = old_errors + new_errors
        if all_errors:
            lim = max(abs(min(all_errors)), abs(max(all_errors))) * 1.1
            lim = min(lim, 5)  # Cap at 500%
        else:
            lim = 2
        
        ax.axhline(y=0, color="gray", linestyle="-", alpha=0.3)
        ax.axvline(x=0, color="gray", linestyle="-", alpha=0.3)
        ax.plot([-lim, lim], [-lim, lim], "k--", alpha=0.3, label="변화 없음")
        ax.set_xlabel("기존 프롬프트 오차율")
        ax.set_ylabel("개선 프롬프트 오차율")
        ax.set_title(f"{metric_title} 오차 변화")
        ax.set_xlim(-lim, lim)
        ax.set_ylim(-lim, lim)
        ax.set_aspect("equal")
        ax.legend(loc="upper left", fontsize=8)
    
    # Hide unused subplot
    axes[1, 2].axis("off")
    
    plt.tight_layout()
    
    scatter_path = f"{output_prefix}_scatter.png"
    plt.savefig(scatter_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Scatter plot saved: {scatter_path}")


def write_stats_report(stats: dict, output_prefix: str, title: str = ""):
    """Write statistics report to markdown file."""
    report_path = f"{output_prefix}_stats.md"
    
    content = f"""# 프롬프트 비교 결과{f': {title}' if title else ''}

## 요약
- 총 비교 건수: {stats['count']}건
- 무게 개선: {stats['weight_improved_count']}건 ({stats['weight_improved_pct']:.1f}%)
- 부피 개선: {stats['volume_improved_count']}건 ({stats['volume_improved_pct']:.1f}%)

## 평균 절대 오차율 (MAE)

| 지표 | 기존 프롬프트 | 개선 프롬프트 | 변화 |
|------|---------------|---------------|------|
| 무게 | {stats['old_weight_mae']*100:.1f}% | {stats['new_weight_mae']*100:.1f}% | {(stats['new_weight_mae'] - stats['old_weight_mae'])*100:+.1f}%p |
| 부피 | {stats['old_volume_mae']*100:.1f}% | {stats['new_volume_mae']*100:.1f}% | {(stats['new_volume_mae'] - stats['old_volume_mae'])*100:+.1f}%p |

## 치수별 MAE (개선 프롬프트)

| 치수 | MAE |
|------|-----|
| Max (최대) | {stats['dim_max_mae']*100:.1f}% |
| Mid (중간) | {stats['dim_mid_mae']*100:.1f}% |
| Min (최소) | {stats['dim_min_mae']*100:.1f}% |

## 해석
- 무게 MAE: {stats['old_weight_mae']*100:.1f}% → {stats['new_weight_mae']*100:.1f}% ({'개선' if stats['new_weight_mae'] < stats['old_weight_mae'] else '악화'})
- 부피 MAE: {stats['old_volume_mae']*100:.1f}% → {stats['new_volume_mae']*100:.1f}% ({'개선' if stats['new_volume_mae'] < stats['old_volume_mae'] else '악화'})
"""
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"Stats report saved: {report_path}")


def run_comparison(
    input_file: str,
    output_prefix: str,
    title: str = "",
):
    """Run full comparison analysis."""
    
    print(f"Input: {input_file}")
    print(f"Output prefix: {output_prefix}")
    print("-" * 80)
    
    # Load data
    data = load_comparison_data(input_file)
    print(f"Loaded {len(data)} records")
    
    if len(data) == 0:
        print("No data to compare!")
        return 0
    
    # Calculate stats
    stats = calculate_stats(data)
    
    # Print summary
    print(f"\n=== Summary ===")
    print(f"Weight improved: {stats['weight_improved_count']}/{stats['count']} ({stats['weight_improved_pct']:.1f}%)")
    print(f"Volume improved: {stats['volume_improved_count']}/{stats['count']} ({stats['volume_improved_pct']:.1f}%)")
    print(f"Weight MAE: {stats['old_weight_mae']*100:.1f}% → {stats['new_weight_mae']*100:.1f}%")
    print(f"Volume MAE: {stats['old_volume_mae']*100:.1f}% → {stats['new_volume_mae']*100:.1f}%")
    
    # Ensure output directory exists
    Path(output_prefix).parent.mkdir(parents=True, exist_ok=True)
    
    # Generate outputs
    plot_error_comparison(data, stats, output_prefix, title)
    plot_scatter_comparison(data, stats, output_prefix, title)
    plot_error_distributions(stats, output_prefix, title)
    write_stats_report(stats, output_prefix, title)
    
    return len(data)


def main():
    parser = argparse.ArgumentParser(
        description="Generate comparison visualizations and statistics"
    )
    parser.add_argument("-i", "--input", required=True,
                        help="Comparison TSV file from merge_results.py")
    parser.add_argument("-o", "--output",
                        help="Output file prefix (default: same directory as input)")
    parser.add_argument("-t", "--title", default="",
                        help="Title for the charts")
    
    args = parser.parse_args()
    
    # Default output: same directory as input, using directory name as prefix
    if args.output:
        output_prefix = args.output
    else:
        input_path = Path(args.input)
        output_prefix = str(input_path.parent / "chart")
    
    count = run_comparison(
        input_file=args.input,
        output_prefix=output_prefix,
        title=args.title,
    )
    
    if count > 0:
        print()
        print("Next step:")
        title_arg = f' -t "{args.title}"' if args.title else ""
        print(f"  uv run python scripts/prompt_variations/compare_line_chart.py \\")
        print(f"    -i {args.input}{title_arg}")
    
    sys.exit(0 if count > 0 else 1)


if __name__ == "__main__":
    main()
