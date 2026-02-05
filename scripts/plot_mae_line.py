#!/usr/bin/env python3
"""Plot MAE line chart."""

import csv
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from pathlib import Path
import argparse

# Korean font setup
font_paths = [
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
]
for path in font_paths:
    if Path(path).exists():
        fm.fontManager.addfont(path)
        plt.rcParams["font.family"] = fm.FontProperties(fname=path).get_name()
        break
plt.rcParams["axes.unicode_minus"] = False

parser = argparse.ArgumentParser()
parser.add_argument("-i", "--input", required=True)
parser.add_argument("-t", "--title", default="v4 Weight MAE 비교")
args = parser.parse_args()

# Load data
data = []
with open(args.input, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f, delimiter="\t")
    for row in reader:
        data.append(row)

print(f"Loaded {len(data)} records")

# Extract absolute errors (MAE)
old_errors = [abs(float(d["old_weight_error"])) for d in data]
new_errors = [abs(float(d["new_weight_error"])) for d in data]

# Sort by old error descending
sorted_indices = sorted(range(len(old_errors)), key=lambda i: old_errors[i], reverse=True)
old_sorted = [old_errors[i] for i in sorted_indices]
new_sorted = [new_errors[i] for i in sorted_indices]

# Plot
fig, ax = plt.subplots(figsize=(16, 5))

n = len(old_sorted)
x = np.arange(n)

ax.fill_between(x, [e*100 for e in old_sorted], alpha=0.4, color='red', label='기존 추정 MAE')
ax.fill_between(x, [e*100 for e in new_sorted], alpha=0.4, color='blue', label='v4 추정 MAE')
ax.plot(x, [e*100 for e in old_sorted], color='red', linewidth=0.5, alpha=0.8)
ax.plot(x, [e*100 for e in new_sorted], color='blue', linewidth=0.5, alpha=0.8)

ax.set_xlabel('상품 순서 (오차 큰 순)')
ax.set_ylabel('오차율 (%)')
ax.set_title(args.title)
ax.legend(loc='upper right')

# Y축 범위 제한
ax.set_ylim(0, 150)

plt.tight_layout()
output_path = str(Path(args.input).parent / "line_chart_mae_sorted.png")
plt.savefig(output_path, dpi=150, bbox_inches='tight')
plt.close()

print(f"Saved: {output_path}")

# Summary
old_mae = np.mean(old_errors) * 100
new_mae = np.mean(new_errors) * 100
print(f"MAE: {old_mae:.1f}% -> {new_mae:.1f}%")
