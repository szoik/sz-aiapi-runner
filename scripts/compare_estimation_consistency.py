#!/usr/bin/env python3
"""
동일 데이터셋에 대한 반복 추정 일관성 비교 그래프
4개 날짜의 결과를 품목별로 비교하여 추정 편차를 시각화
"""

import json
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
from pathlib import Path

matplotlib.rcParams['font.family'] = ['AppleGothic', 'Malgun Gothic', 'sans-serif']
matplotlib.rcParams['axes.unicode_minus'] = False

def parse_volume(vol_str):
    """WxDxH 문자열을 파싱하여 (width, depth, height) 반환"""
    if not vol_str or vol_str == "0":
        return (0, 0, 0)
    parts = str(vol_str).lower().split('x')
    if len(parts) == 3:
        try:
            return (float(parts[0]), float(parts[1]), float(parts[2]))
        except ValueError:
            return (0, 0, 0)
    return (0, 0, 0)

def load_results(filepath):
    """JSONL 파일에서 결과를 로드하여 id 기준 dict로 반환"""
    results = {}
    with open(filepath) as f:
        for line in f:
            d = json.loads(line.strip())
            item_id = d['id']
            w, dep, h = parse_volume(d.get('volume', '0x0x0'))
            results[item_id] = {
                'productName': d.get('productName', ''),
                'width': w,
                'depth': dep,
                'height': h,
                'weight': d.get('weight', 0),
            }
    return results

def main():
    dates = [
        ('20260125-170122-50', '01/25'),
        ('20260126-115845-50', '01/26'),
        ('20260128-135432-50', '01/28'),
        ('20260129-113201-50', '01/29'),
    ]
    colors = ['red', 'green', 'blue', '#DAA520']  # yellow → goldenrod for visibility

    # 데이터 로드
    all_data = {}
    for folder, label in dates:
        filepath = Path(f".local/{folder}/result.jsonl")
        all_data[label] = load_results(filepath)

    # 공통 품목 ID 추출 (id 기준 정렬)
    common_ids = set(all_data[dates[0][1]].keys())
    for label in [d[1] for d in dates]:
        common_ids &= set(all_data[label].keys())
    common_ids = sorted(common_ids, key=lambda x: int(x))

    print(f"공통 품목 수: {len(common_ids)}")

    # 품목명 목록
    product_names = [all_data[dates[0][1]][pid]['productName'][:20] for pid in common_ids]

    metrics = ['width', 'depth', 'height', 'weight']
    metric_labels = ['Width (cm)', 'Depth (cm)', 'Height (cm)', 'Weight (kg)']

    # 4개 지표 × 1 그래프
    fig, axes = plt.subplots(4, 1, figsize=(20, 24))
    fig.suptitle('추정 일관성 비교 (동일 데이터셋, 4회 반복)', fontsize=16, fontweight='bold')

    x = np.arange(len(common_ids))
    bar_width = 0.2

    for idx, (metric, metric_label) in enumerate(zip(metrics, metric_labels)):
        ax = axes[idx]

        for i, (folder, label) in enumerate(dates):
            values = [all_data[label][pid][metric] for pid in common_ids]
            ax.bar(x + i * bar_width, values, bar_width,
                   label=label, color=colors[i], alpha=0.8)

        ax.set_ylabel(metric_label, fontsize=12)
        ax.set_xticks(x + bar_width * 1.5)
        ax.set_xticklabels([f"#{pid}" for pid in common_ids], rotation=90, fontsize=7)
        ax.legend(fontsize=10)
        ax.grid(axis='y', alpha=0.3)

    plt.tight_layout(rect=[0, 0, 1, 0.97])

    output_path = Path(".local/estimation_consistency_comparison.png")
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"그래프 저장: {output_path}")

    # 편차 통계
    print("\n" + "=" * 80)
    print("품목별 추정 편차 통계 (4회 반복 간 표준편차)")
    print("=" * 80)
    print(f"{'ID':>4} {'품목명':<22} {'Width SD':>10} {'Depth SD':>10} {'Height SD':>10} {'Weight SD':>10}")
    print("-" * 80)

    total_sd = {'width': [], 'depth': [], 'height': [], 'weight': []}

    for pid in common_ids:
        values = {m: [] for m in metrics}
        for _, label in dates:
            for m in metrics:
                values[m].append(all_data[label][pid][m])

        sds = {m: np.std(values[m]) for m in metrics}
        name = all_data[dates[0][1]][pid]['productName'][:20]

        for m in metrics:
            total_sd[m].append(sds[m])

        # 편차가 큰 품목만 출력
        if any(sds[m] > 0 for m in metrics):
            print(f"#{pid:>3} {name:<22} {sds['width']:>10.2f} {sds['depth']:>10.2f} {sds['height']:>10.2f} {sds['weight']:>10.3f}")

    print("-" * 80)
    print(f"{'평균':>4} {'':22} {np.mean(total_sd['width']):>10.2f} {np.mean(total_sd['depth']):>10.2f} {np.mean(total_sd['height']):>10.2f} {np.mean(total_sd['weight']):>10.3f}")

    # 일관성 요약
    print("\n" + "=" * 80)
    print("일관성 요약")
    print("=" * 80)
    for m, label in zip(metrics, metric_labels):
        vals_by_item = []
        for pid in common_ids:
            item_vals = [all_data[d[1]][pid][m] for d in dates]
            if max(item_vals) > 0:
                cv = np.std(item_vals) / np.mean(item_vals) * 100
                vals_by_item.append(cv)
        if vals_by_item:
            print(f"{label}: 평균 변동계수(CV) = {np.mean(vals_by_item):.1f}%, 최대 CV = {max(vals_by_item):.1f}%")

if __name__ == "__main__":
    main()
