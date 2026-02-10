#!/usr/bin/env python3
"""
11개 카테고리에 보정 계수 적용하여 효과 검증
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json

def load_correction_config():
    """보정 계수 설정 로드"""
    with open(".local/weight_correction_config.json") as f:
        return json.load(f)

def get_correction_factor(ai_weight: float, config: list) -> float:
    """AI 추정 무게에 따른 보정 계수 반환"""
    for c in config:
        min_val = c['min']
        max_val = c['max'] if c['max'] is not None else float('inf')
        if min_val <= ai_weight < max_val:
            return c['factor']
    return 1.0  # 기본값

def main():
    config = load_correction_config()
    
    # 카테고리 파일들
    categories = {
        'o01': 'inputs/categories/o01_보이그룹_인형피규어_err50.tsv',
        'o02': 'inputs/categories/o02_방송예능_인형피규어_err50.tsv',
        'o03': 'inputs/categories/o03_바인더_err50.tsv',
        'o04': 'inputs/categories/o04_키덜트_피규어인형_err50.tsv',
        'o05': 'inputs/categories/o05_토트백_err50.tsv',
        'o06': 'inputs/categories/o06_outlier_err100.tsv',
        'u01': 'inputs/categories/u01_이어폰팁_err50.tsv',
        'u02': 'inputs/categories/u02_볼링가방_err50.tsv',
        'u03': 'inputs/categories/u03_스킨토너_err50.tsv',
        'u04': 'inputs/categories/u04_에센스_err50.tsv',
        'u05': 'inputs/categories/u05_시리얼_err50.tsv',
    }
    
    # v5 결과 폴더
    v5_base = Path(".local/prompt_results/weight-volume.v5.system")
    
    # 전체 비교 데이터 (v0 vs new 비교 파일 - v0 정보 포함)
    comparison_file = Path(".local/parallel_jobs/20260204-221954/comparison_no_outlier.tsv")
    full_df = pd.read_csv(comparison_file, sep="\t")
    
    print("=" * 110)
    print("카테고리별 보정 효과 검증 (v0 + 보정 vs v5)")
    print("=" * 110)
    print(f"{'카테고리':<10} {'유형':<6} {'개수':>6} {'v0 MAE':>10} {'보정 MAE':>10} {'개선':>10} {'v5 MAE':>10} {'보정vs v5':>12}")
    print("-" * 110)
    
    total_results = []
    
    for cat_id, cat_file in categories.items():
        # 카테고리 데이터 로드
        cat_df = pd.read_csv(cat_file, sep="\t")
        order_ids = set(cat_df['order_id'].astype(str))
        
        # 전체 데이터에서 해당 카테고리 추출
        subset = full_df[full_df['order_id'].astype(str).isin(order_ids)].copy()
        
        if len(subset) == 0:
            print(f"{cat_id:<10} 데이터 없음")
            continue
        
        # v0 무게 (old_weight_kg)
        subset['ai_weight'] = subset['old_weight_kg']
        subset['weight'] = subset['actual_weight']
        
        # 보정 적용
        subset['corrected_weight'] = subset['ai_weight'].apply(
            lambda x: x * get_correction_factor(x, config)
        )
        
        # MAE 계산
        valid = subset['weight'] > 0
        v0_mae = (abs(subset.loc[valid, 'ai_weight'] - subset.loc[valid, 'weight']) / subset.loc[valid, 'weight'] * 100).mean()
        corrected_mae = (abs(subset.loc[valid, 'corrected_weight'] - subset.loc[valid, 'weight']) / subset.loc[valid, 'weight'] * 100).mean()
        
        # v5 결과 찾기
        cat_name = Path(cat_file).stem  # 파일명에서 확장자 제거
        v5_dirs = sorted(v5_base.glob(f"*-{cat_name}"))
        
        v5_mae = None
        for d in reversed(v5_dirs):
            # comparison.tsv 또는 merge_result.tsv
            for fname in ["comparison.tsv", "merge_result.tsv"]:
                merge_file = d / fname
                if merge_file.exists():
                    v5_df = pd.read_csv(merge_file, sep="\t")
                    # 컬럼명 확인
                    if 'ai_weight' in v5_df.columns and 'weight' in v5_df.columns:
                        valid_v5 = v5_df['weight'] > 0
                        v5_mae = (abs(v5_df.loc[valid_v5, 'ai_weight'] - v5_df.loc[valid_v5, 'weight']) / v5_df.loc[valid_v5, 'weight'] * 100).mean()
                    elif 'new_weight_kg' in v5_df.columns and 'actual_weight' in v5_df.columns:
                        valid_v5 = v5_df['actual_weight'] > 0
                        v5_mae = (abs(v5_df.loc[valid_v5, 'new_weight_kg'] - v5_df.loc[valid_v5, 'actual_weight']) / v5_df.loc[valid_v5, 'actual_weight'] * 100).mean()
                    break
            if v5_mae is not None:
                break
        
        cat_type = "과대" if cat_id.startswith('o') else "과소"
        improvement = v0_mae - corrected_mae
        
        v5_str = f"{v5_mae:.1f}%" if v5_mae else "N/A"
        vs_v5 = ""
        if v5_mae:
            diff = corrected_mae - v5_mae
            vs_v5 = f"{diff:+.1f}%p"
        
        print(f"{cat_id:<10} {cat_type:<6} {len(subset):>6} {v0_mae:>10.1f}% {corrected_mae:>10.1f}% {improvement:>+10.1f}%p {v5_str:>10} {vs_v5:>12}")
        
        total_results.append({
            'cat_id': cat_id,
            'type': cat_type,
            'count': len(subset),
            'v0_mae': v0_mae,
            'corrected_mae': corrected_mae,
            'v5_mae': v5_mae
        })
    
    # 전체 평균
    print("-" * 100)
    avg_v0 = np.mean([r['v0_mae'] for r in total_results])
    avg_corrected = np.mean([r['corrected_mae'] for r in total_results])
    avg_v5 = np.mean([r['v5_mae'] for r in total_results if r['v5_mae']])
    
    print(f"{'평균':<10} {'':<6} {'':<6} {avg_v0:>10.1f}% {avg_corrected:>10.1f}% {avg_v0-avg_corrected:>+10.1f}%p {avg_v5:>10.1f}%")
    
    # 유형별 평균
    print("\n" + "=" * 100)
    print("유형별 평균")
    print("=" * 100)
    
    for t in ["과대", "과소"]:
        subset = [r for r in total_results if r['type'] == t]
        if subset:
            avg_v0 = np.mean([r['v0_mae'] for r in subset])
            avg_corrected = np.mean([r['corrected_mae'] for r in subset])
            avg_v5 = np.mean([r['v5_mae'] for r in subset if r['v5_mae']])
            print(f"{t}추정 카테고리: v0 {avg_v0:.1f}% → 보정 {avg_corrected:.1f}% (개선: {avg_v0-avg_corrected:+.1f}%p), v5: {avg_v5:.1f}%")

if __name__ == "__main__":
    main()
