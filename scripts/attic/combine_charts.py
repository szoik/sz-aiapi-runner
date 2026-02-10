#!/usr/bin/env python3
"""
Combine Charts Script

Combine 4 chart images into a single summary image for each category.

Layout:
    ┌─────────────────────────────────────────┐
    │  chart_comparison.png │ chart_scatter.png │  ← 정사각 2개 (상단)
    ├─────────────────────────────────────────┤
    │         line_chart_original.png          │  ← 가로로 긴 사각 (중단)
    ├─────────────────────────────────────────┤
    │         line_chart_sorted.png            │  ← 가로로 긴 사각 (하단)
    └─────────────────────────────────────────┘

Usage:
    uv run python scripts/combine_charts.py

    # Custom input/output
    uv run python scripts/combine_charts.py \
        -i .local/prompt_results/weight-volume.v2.system \
        -o .local/prompt_results/weight-volume.v2.system/summary
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


def combine_charts(
    input_dir: str,
    output_path: str,
    category_name: str,
) -> bool:
    """Combine 4 charts into one image."""
    
    input_path = Path(input_dir)
    
    # Required files
    files = {
        "comparison": input_path / "chart_comparison.png",
        "scatter": input_path / "chart_scatter.png",
        "line_original": input_path / "line_chart_original.png",
        "line_sorted": input_path / "line_chart_sorted.png",
    }
    
    # Check all files exist
    for name, path in files.items():
        if not path.exists():
            print(f"  Missing: {name} ({path})")
            return False
    
    # Load images
    img_comparison = Image.open(files["comparison"])
    img_scatter = Image.open(files["scatter"])
    img_line_original = Image.open(files["line_original"])
    img_line_sorted = Image.open(files["line_sorted"])
    
    # Get dimensions
    # Top row: two square images side by side
    top_width = img_comparison.width + img_scatter.width
    top_height = max(img_comparison.height, img_scatter.height)
    
    # Line charts width (should match top row width)
    line_width = max(top_width, img_line_original.width, img_line_sorted.width)
    
    # Resize line charts to match width if needed
    if img_line_original.width != line_width:
        ratio = line_width / img_line_original.width
        new_height = int(img_line_original.height * ratio)
        img_line_original = img_line_original.resize((line_width, new_height), Image.Resampling.LANCZOS)
    
    if img_line_sorted.width != line_width:
        ratio = line_width / img_line_sorted.width
        new_height = int(img_line_sorted.height * ratio)
        img_line_sorted = img_line_sorted.resize((line_width, new_height), Image.Resampling.LANCZOS)
    
    # Resize top images to fit half width each
    half_width = line_width // 2
    
    # Resize comparison
    ratio = half_width / img_comparison.width
    comp_new_height = int(img_comparison.height * ratio)
    img_comparison = img_comparison.resize((half_width, comp_new_height), Image.Resampling.LANCZOS)
    
    # Resize scatter
    ratio = half_width / img_scatter.width
    scatter_new_height = int(img_scatter.height * ratio)
    img_scatter = img_scatter.resize((half_width, scatter_new_height), Image.Resampling.LANCZOS)
    
    # Top row height (use max)
    top_height = max(img_comparison.height, img_scatter.height)
    
    # Total dimensions
    total_width = line_width
    total_height = top_height + img_line_original.height + img_line_sorted.height
    
    # Create combined image
    combined = Image.new("RGB", (total_width, total_height), color="white")
    
    # Paste images
    # Top row
    combined.paste(img_comparison, (0, 0))
    combined.paste(img_scatter, (half_width, 0))
    
    # Line charts
    combined.paste(img_line_original, (0, top_height))
    combined.paste(img_line_sorted, (0, top_height + img_line_original.height))
    
    # Save
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    combined.save(output_path, quality=95)
    
    print(f"  Saved: {output_path}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Combine chart images into summary"
    )
    parser.add_argument("-i", "--input-base",
                        default=".local/prompt_results/weight-volume.v2.system",
                        help="Base directory containing category folders")
    parser.add_argument("-o", "--output-dir",
                        default=".local/prompt_results/weight-volume.v2.system/summary",
                        help="Output directory for combined images")
    
    args = parser.parse_args()
    
    # Categories to process
    categories = [
        "o01_보이그룹_인형피규어",
        "o02_방송예능_인형피규어",
        "o03_바인더",
        "o04_키덜트_피규어인형",
        "o05_토트백",
        "u01_이어폰팁",
        "u02_볼링가방",
        "u03_스킨토너",
        "u04_에센스",
        "u05_시리얼",
    ]
    
    success = 0
    for cat in categories:
        print(f"Processing: {cat}")
        input_dir = f"{args.input_base}/{cat}"
        output_path = f"{args.output_dir}/{cat}.png"
        
        if combine_charts(input_dir, output_path, cat):
            success += 1
    
    print(f"\nDone: {success}/{len(categories)} combined")


if __name__ == "__main__":
    main()
