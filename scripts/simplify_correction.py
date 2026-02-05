#!/usr/bin/env python3
"""
보정 계수를 더 단순한 구간으로 최적화
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json

def find_optimal_factor(weights_ai, weights_actual, search_range=(0.5, 5.0), step=0.01):
    """MAE를 최소화하는 보정 계수 찾기"""
    best_factor = 1.0
    best_mae = float('inf')
    
    valid = weights_actual > 0
    if not valid.any():
        return 1.0, 0
    
    for factor in np.arange(search_range[0], search_range[1], step):
        corrected = weights_ai[valid] * factor
        mae = (abs(corrected - weights_actual[valid]) / weights_actual[valid] * 100).mean()
        if mae < best_mae:
            best_mae = mae
            best_factor = factor
    
    return best_factor, best_mae

def main():
    # 데이터 로드
    comparison_file = Path(".local/parallel_jobs/20260204-221954/comparison_no_outlier.tsv")
    df = pd.read_csv(comparison_file, sep="\t")
    
    df['ai_weight'] = df['old_weight_kg']
    df['weight'] = df['actual_weight']
    
    print(f"총 데이터: {len(df)}개\n")
    
    # 원본 MAE
    valid = df['weight'] > 0
    original_mae = (abs(df.loc[valid, 'ai_weight'] - df.loc[valid, 'weight']) / df.loc[valid, 'weight'] * 100).mean()
    print(f"원본 MAE: {original_mae:.2f}%\n")
    
    # 단순화된 구간들 테스트
    simple_bins_options = [
        # 5구간
        ([0, 0.1, 0.5, 1.0, 2.0, float('inf')], "5구간"),
        # 6구간
        ([0, 0.1, 0.3, 0.5, 1.0, 2.0, float('inf')], "6구간"),
        # 7구간
        ([0, 0.1, 0.3, 0.5, 1.0, 2.0, 5.0, float('inf')], "7구간"),
        # 8구간
        ([0, 0.05, 0.1, 0.3, 0.5, 1.0, 2.0, 5.0, float('inf')], "8구간"),
    ]
    
    best_overall_mae = float('inf')
    best_config = None
    best_name = None
    
    for bins, name in simple_bins_options:
        print(f"\n{'='*80}")
        print(f"{name} 테스트")
        print(f"{'='*80}")
        
        corrections = []
        df['corrected'] = df['ai_weight'].copy()
        
        for i in range(len(bins) - 1):
            low, high = bins[i], bins[i+1]
            label = f"{low}-{high}" if high != float('inf') else f"{low}+"
            
            mask = (df['ai_weight'] >= low) & (df['ai_weight'] < high)
            subset = df[mask]
            
            if len(subset) < 10:
                corrections.append({'min': low, 'max': high if high != float('inf') else None, 'factor': 1.0})
                continue
            
            best_factor, best_mae = find_optimal_factor(
                subset['ai_weight'].values,
                subset['weight'].values
            )
            
            corrections.append({
                'min': low,
                'max': high if high != float('inf') else None,
                'factor': round(best_factor, 2)
            })
            
            df.loc[mask, 'corrected'] = df.loc[mask, 'ai_weight'] * best_factor
            
            orig_mae = (abs(subset['ai_weight'] - subset['weight']) / subset['weight'] * 100).mean()
            print(f"{label:<15} 개수: {len(subset):>5}, 최적계수: {best_factor:.2f}, 원본MAE: {orig_mae:.1f}%, 보정MAE: {best_mae:.1f}%")
        
        # 전체 MAE
        corrected_mae = (abs(df.loc[valid, 'corrected'] - df.loc[valid, 'weight']) / df.loc[valid, 'weight'] * 100).mean()
        print(f"\n전체 MAE: {original_mae:.2f}% → {corrected_mae:.2f}% (개선: {original_mae - corrected_mae:.2f}%p)")
        
        if corrected_mae < best_overall_mae:
            best_overall_mae = corrected_mae
            best_config = corrections
            best_name = name
    
    # 최적 구간 출력
    print(f"\n\n{'='*80}")
    print(f"최적 구간: {best_name}")
    print(f"전체 MAE: {best_overall_mae:.2f}%")
    print(f"개선: {original_mae - best_overall_mae:.2f}%p")
    print(f"{'='*80}")
    
    print("\n보정 계수:")
    for c in best_config:
        max_str = c['max'] if c['max'] else "∞"
        print(f"  {c['min']}kg ~ {max_str}kg: × {c['factor']}")
    
    # 저장
    config_path = Path(".local/weight_correction_simple.json")
    with open(config_path, 'w') as f:
        json.dump(best_config, f, indent=2)
    print(f"\n저장: {config_path}")

if __name__ == "__main__":
    main()
