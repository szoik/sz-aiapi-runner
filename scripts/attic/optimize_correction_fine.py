#!/usr/bin/env python3
"""
더 세밀한 구간으로 최적 보정 계수 탐색

Usage:
    python scripts/attic/optimize_correction_fine.py \\
        -i .local/parallel_jobs/20260204-221954/comparison_no_outlier.tsv \\
        -o .local/weight_correction_config.json
"""

import argparse
import pandas as pd
import numpy as np
from pathlib import Path
import json


def find_optimal_factor(weights_ai, weights_actual, search_range=(0.5, 4.0), step=0.01):
    """MAE를 최소화하는 보정 계수 찾기"""
    best_factor = 1.0
    best_mae = float('inf')
    
    for factor in np.arange(search_range[0], search_range[1], step):
        corrected = weights_ai * factor
        # 0으로 나누기 방지
        valid = weights_actual > 0
        mae = (abs(corrected[valid] - weights_actual[valid]) / weights_actual[valid] * 100).mean()
        if mae < best_mae:
            best_mae = mae
            best_factor = factor
    
    return best_factor, best_mae

def main():
    parser = argparse.ArgumentParser(
        description="더 세밀한 구간으로 최적 보정 계수 탐색",
        epilog="예시: python scripts/attic/optimize_correction_fine.py -i .local/parallel_jobs/.../comparison.tsv -o .local/weight_correction_config.json"
    )
    parser.add_argument("-i", "--input", required=True, help="입력 TSV 파일 (비교 결과)")
    parser.add_argument("-o", "--output", required=True, help="보정 계수 설정 JSON 출력 파일")
    args = parser.parse_args()

    # 데이터 로드
    comparison_file = Path(args.input)
    df = pd.read_csv(comparison_file, sep="\t")
    
    df['ai_weight'] = df['old_weight_kg']
    df['weight'] = df['actual_weight']
    
    print(f"총 데이터: {len(df)}개\n")
    
    # 원본 MAE
    valid = df['weight'] > 0
    original_mae = (abs(df.loc[valid, 'ai_weight'] - df.loc[valid, 'weight']) / df.loc[valid, 'weight'] * 100).mean()
    print(f"원본 MAE: {original_mae:.2f}%\n")
    
    # 더 세밀한 구간 (20개)
    ai_bins = [0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, float('inf')]
    
    print("=" * 90)
    print("세밀한 구간별 최적 보정 계수")
    print("=" * 90)
    print(f"{'구간':<15} {'개수':>6} {'평균AI':>10} {'평균실제':>10} {'최적계수':>10} {'원본MAE':>10} {'보정MAE':>10}")
    print("-" * 90)
    
    corrections = {}
    df['corrected_weight'] = df['ai_weight'].copy()
    
    for i in range(len(ai_bins) - 1):
        low, high = ai_bins[i], ai_bins[i+1]
        label = f"{low}-{high}" if high != float('inf') else f"{low}+"
        
        mask = (df['ai_weight'] >= low) & (df['ai_weight'] < high)
        subset = df[mask]
        
        if len(subset) < 10:
            # 데이터가 너무 적으면 스킵
            continue
        
        avg_ai = subset['ai_weight'].mean()
        avg_actual = subset['weight'].mean()
        
        # 최적 보정 계수 찾기
        best_factor, best_mae = find_optimal_factor(
            subset['ai_weight'].values,
            subset['weight'].values,
            search_range=(0.5, 5.0),
            step=0.01
        )
        
        # 원본 MAE
        orig_mae = (abs(subset['ai_weight'] - subset['weight']) / subset['weight'] * 100).mean()
        
        corrections[(low, high)] = best_factor
        df.loc[mask, 'corrected_weight'] = df.loc[mask, 'ai_weight'] * best_factor
        
        print(f"{label:<15} {len(subset):>6} {avg_ai:>10.3f} {avg_actual:>10.3f} {best_factor:>10.2f} {orig_mae:>10.1f}% {best_mae:>10.1f}%")
    
    # 최종 결과
    corrected_mae = (abs(df.loc[valid, 'corrected_weight'] - df.loc[valid, 'weight']) / df.loc[valid, 'weight'] * 100).mean()
    
    print("\n" + "=" * 90)
    print(f"최종 결과")
    print("=" * 90)
    print(f"원본 MAE: {original_mae:.2f}%")
    print(f"보정 후 MAE: {corrected_mae:.2f}%")
    print(f"개선: {original_mae - corrected_mae:.2f}%p")
    
    # 보정 계수 저장
    correction_config = []
    for (low, high), factor in sorted(corrections.items()):
        correction_config.append({
            'min': low,
            'max': high if high != float('inf') else None,
            'factor': round(factor, 2)
        })
    
    config_path = Path(args.output)
    with open(config_path, 'w') as f:
        json.dump(correction_config, f, indent=2)
    print(f"\n보정 계수 저장: {config_path}")
    
    # 에러 분포 분석
    print("\n" + "=" * 90)
    print("에러 분포 비교")
    print("=" * 90)
    
    df['original_error'] = (df['ai_weight'] - df['weight']) / df['weight'] * 100
    df['corrected_error'] = (df['corrected_weight'] - df['weight']) / df['weight'] * 100
    
    for percentile in [10, 25, 50, 75, 90]:
        orig_p = np.percentile(df['original_error'], percentile)
        corr_p = np.percentile(df['corrected_error'], percentile)
        print(f"P{percentile:02d}: 원본 {orig_p:+.1f}%, 보정 후 {corr_p:+.1f}%")
    
    # 과대/과소 추정 비율
    print("\n" + "=" * 90)
    print("과대/과소 추정 비율")
    print("=" * 90)
    
    orig_over = (df['ai_weight'] > df['weight']).sum()
    orig_under = (df['ai_weight'] < df['weight']).sum()
    corr_over = (df['corrected_weight'] > df['weight']).sum()
    corr_under = (df['corrected_weight'] < df['weight']).sum()
    
    print(f"원본: 과대추정 {orig_over} ({orig_over/len(df)*100:.1f}%), 과소추정 {orig_under} ({orig_under/len(df)*100:.1f}%)")
    print(f"보정: 과대추정 {corr_over} ({corr_over/len(df)*100:.1f}%), 과소추정 {corr_under} ({corr_under/len(df)*100:.1f}%)")

if __name__ == "__main__":
    main()
