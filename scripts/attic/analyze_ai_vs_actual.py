#!/usr/bin/env python3
"""
AI 추정값 vs 실제 무게의 관계 분석
비선형 보정 함수를 찾기 위한 분석

Usage:
    python scripts/attic/analyze_ai_vs_actual.py -i .local/parallel_jobs/20260204-221954/comparison_no_outlier.tsv
"""

import argparse
import pandas as pd
import numpy as np
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="AI 추정값 vs 실제 무게 관계 분석",
        epilog="예시: python scripts/attic/analyze_ai_vs_actual.py -i .local/parallel_jobs/20260204-221954/comparison_no_outlier.tsv"
    )
    parser.add_argument("-i", "--input", required=True, help="입력 TSV 파일 (비교 결과)")
    args = parser.parse_args()

    # 데이터 로드
    comparison_file = Path(args.input)
    df = pd.read_csv(comparison_file, sep="\t")
    
    # 컬럼명 정규화 (old = v0 기준)
    df['ai_weight'] = df['old_weight_kg']
    df['weight'] = df['actual_weight']
    
    print(f"총 데이터: {len(df)}개\n")
    
    # AI 추정 무게 구간별로 실제 무게 분포 분석
    ai_bins = [0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0, 3.0, 5.0, float('inf')]
    ai_labels = ['0-0.1', '0.1-0.2', '0.2-0.3', '0.3-0.5', '0.5-0.7', '0.7-1.0', '1.0-1.5', '1.5-2.0', '2.0-3.0', '3.0-5.0', '5.0+']
    
    df['ai_bin'] = pd.cut(df['ai_weight'], bins=ai_bins, labels=ai_labels, right=False)
    
    print("=" * 80)
    print("AI 추정 구간별 실제 무게 분포 분석")
    print("=" * 80)
    print(f"{'AI구간':<12} {'개수':>6} {'평균AI':>10} {'평균실제':>10} {'실제/AI':>10} {'중앙AI':>10} {'중앙실제':>10} {'최적보정':>10}")
    print("-" * 80)
    
    corrections = []
    
    for label in ai_labels:
        subset = df[df['ai_bin'] == label]
        if len(subset) == 0:
            continue
            
        avg_ai = subset['ai_weight'].mean()
        avg_actual = subset['weight'].mean()
        median_ai = subset['ai_weight'].median()
        median_actual = subset['weight'].median()
        
        # 실제/AI 비율 (보정 계수)
        ratio = avg_actual / avg_ai if avg_ai > 0 else 1.0
        median_ratio = median_actual / median_ai if median_ai > 0 else 1.0
        
        # 최적 보정 계수: MAE를 최소화하는 값 찾기
        best_factor = 1.0
        best_mae = float('inf')
        for factor in np.arange(0.5, 3.0, 0.05):
            corrected = subset['ai_weight'] * factor
            mae = (abs(corrected - subset['weight']) / subset['weight'] * 100).mean()
            if mae < best_mae:
                best_mae = mae
                best_factor = factor
        
        corrections.append({
            'bin': label,
            'count': len(subset),
            'avg_ai': avg_ai,
            'avg_actual': avg_actual,
            'ratio': ratio,
            'optimal_factor': best_factor,
            'optimal_mae': best_mae
        })
        
        print(f"{label:<12} {len(subset):>6} {avg_ai:>10.3f} {avg_actual:>10.3f} {ratio:>10.2f} {median_ai:>10.3f} {median_actual:>10.3f} {best_factor:>10.2f}")
    
    print("\n")
    print("=" * 80)
    print("최적 보정 계수 적용 시뮬레이션")
    print("=" * 80)
    
    # 원본 MAE
    original_mae = (abs(df['ai_weight'] - df['weight']) / df['weight'] * 100).mean()
    print(f"원본 MAE: {original_mae:.2f}%")
    
    # 최적 보정 계수 적용
    df['corrected_weight'] = df['ai_weight'].copy()
    for c in corrections:
        mask = df['ai_bin'] == c['bin']
        df.loc[mask, 'corrected_weight'] = df.loc[mask, 'ai_weight'] * c['optimal_factor']
    
    corrected_mae = (abs(df['corrected_weight'] - df['weight']) / df['weight'] * 100).mean()
    print(f"보정 후 MAE: {corrected_mae:.2f}%")
    print(f"개선: {original_mae - corrected_mae:.2f}%p")
    
    # 구간별 MAE 비교
    print("\n")
    print("=" * 80)
    print("구간별 MAE 비교 (원본 vs 보정)")
    print("=" * 80)
    print(f"{'AI구간':<12} {'개수':>6} {'원본MAE':>12} {'보정MAE':>12} {'개선':>10}")
    print("-" * 80)
    
    for label in ai_labels:
        subset = df[df['ai_bin'] == label]
        if len(subset) == 0:
            continue
        
        orig_mae = (abs(subset['ai_weight'] - subset['weight']) / subset['weight'] * 100).mean()
        corr_mae = (abs(subset['corrected_weight'] - subset['weight']) / subset['weight'] * 100).mean()
        
        print(f"{label:<12} {len(subset):>6} {orig_mae:>12.1f}% {corr_mae:>12.1f}% {orig_mae - corr_mae:>+10.1f}%p")
    
    # 회귀 분석으로 연속 보정 함수 찾기
    print("\n")
    print("=" * 80)
    print("회귀 분석: AI 추정값 → 실제 무게 관계")
    print("=" * 80)
    
    # 로그 변환 선형 회귀
    valid = (df['ai_weight'] > 0) & (df['weight'] > 0)
    log_ai = np.log(df.loc[valid, 'ai_weight'])
    log_actual = np.log(df.loc[valid, 'weight'])
    
    # 선형 회귀 (log-log space)
    coeffs = np.polyfit(log_ai, log_actual, 1)
    print(f"log(실제) = {coeffs[0]:.4f} * log(AI) + {coeffs[1]:.4f}")
    print(f"즉, 실제 = exp({coeffs[1]:.4f}) * AI^{coeffs[0]:.4f}")
    print(f"     실제 = {np.exp(coeffs[1]):.4f} * AI^{coeffs[0]:.4f}")
    
    # 회귀 기반 보정 적용
    df.loc[valid, 'regression_corrected'] = np.exp(coeffs[1]) * (df.loc[valid, 'ai_weight'] ** coeffs[0])
    regression_mae = (abs(df.loc[valid, 'regression_corrected'] - df.loc[valid, 'weight']) / df.loc[valid, 'weight'] * 100).mean()
    print(f"\n회귀 보정 MAE: {regression_mae:.2f}%")
    print(f"원본 대비 개선: {original_mae - regression_mae:.2f}%p")

if __name__ == "__main__":
    main()
