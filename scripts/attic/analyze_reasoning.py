#!/usr/bin/env python3
"""
v5 reasoning과 추정 오차의 상관관계 분석

Usage:
    python scripts/attic/analyze_reasoning.py -i .local/parallel_jobs/20260204-221954/comparison_no_outlier.tsv
"""

import argparse
import pandas as pd
import numpy as np
from pathlib import Path
import re
from collections import Counter


def main():
    parser = argparse.ArgumentParser(
        description="reasoning과 추정 오차 상관관계 분석",
        epilog="예시: python scripts/attic/analyze_reasoning.py -i .local/parallel_jobs/20260204-221954/comparison_no_outlier.tsv"
    )
    parser.add_argument("-i", "--input", required=True, help="입력 TSV 파일 (비교 결과)")
    args = parser.parse_args()

    # 데이터 로드
    df = pd.read_csv(args.input, sep="\t")
    
    # 에러 계산 (v5 기준)
    df['v5_error'] = (df['new_weight_kg'] - df['actual_weight']) / df['actual_weight'] * 100
    df['v5_abs_error'] = abs(df['v5_error'])
    
    # v0 에러도
    df['v0_error'] = (df['old_weight_kg'] - df['actual_weight']) / df['actual_weight'] * 100
    df['v0_abs_error'] = abs(df['v0_error'])
    
    print(f"총 데이터: {len(df)}개\n")
    
    # reasoning에서 키워드 추출
    keywords = [
        'light', 'heavy', 'minimal', 'compact', 'small', 'large', 'big',
        'plastic', 'metal', 'glass', 'liquid', 'fabric', 'paper', 'ceramic',
        'packaging', 'box', 'padding', 'bubble',
        'set', 'multiple', 'single', 'pair',
        'battery', 'electronic',
    ]
    
    print("=" * 90)
    print("키워드별 오차 분석 (v5)")
    print("=" * 90)
    print(f"{'키워드':<15} {'개수':>6} {'평균오차':>12} {'평균절대오차':>12} {'과대추정%':>10} {'과소추정%':>10}")
    print("-" * 90)
    
    keyword_stats = []
    for kw in keywords:
        mask = df['new_reason'].str.lower().str.contains(kw, na=False)
        subset = df[mask]
        if len(subset) < 10:
            continue
        
        avg_error = subset['v5_error'].mean()
        avg_abs_error = subset['v5_abs_error'].mean()
        over = (subset['v5_error'] > 0).sum() / len(subset) * 100
        under = (subset['v5_error'] < 0).sum() / len(subset) * 100
        
        keyword_stats.append({
            'keyword': kw,
            'count': len(subset),
            'avg_error': avg_error,
            'avg_abs_error': avg_abs_error,
            'over_pct': over,
            'under_pct': under
        })
        
        print(f"{kw:<15} {len(subset):>6} {avg_error:>+12.1f}% {avg_abs_error:>12.1f}% {over:>10.1f}% {under:>10.1f}%")
    
    # 오차 크기별 reasoning 패턴
    print("\n\n" + "=" * 90)
    print("오차 크기별 reasoning 패턴 (v5)")
    print("=" * 90)
    
    error_bins = [
        ("정확 (±20%)", -20, 20),
        ("소폭 과대 (20~50%)", 20, 50),
        ("대폭 과대 (50%+)", 50, 1000),
        ("소폭 과소 (-50~-20%)", -50, -20),
        ("대폭 과소 (-50% 미만)", -1000, -50),
    ]
    
    for label, low, high in error_bins:
        if low < high:
            mask = (df['v5_error'] >= low) & (df['v5_error'] < high)
        else:
            mask = (df['v5_error'] >= high) & (df['v5_error'] < low)
        subset = df[mask]
        
        if len(subset) == 0:
            continue
        
        print(f"\n### {label} (n={len(subset)})")
        
        # 키워드 빈도
        word_counter = Counter()
        for reason in subset['new_reason'].dropna():
            words = re.findall(r'\b[a-z]+\b', reason.lower())
            word_counter.update(words)
        
        # 불용어 제거
        stopwords = {'the', 'a', 'an', 'and', 'or', 'is', 'are', 'with', 'for', 'to', 'of', 'in', 'on', 'at', 'it', 'its', 'this', 'that', 'be', 'as', 'by'}
        for sw in stopwords:
            word_counter.pop(sw, None)
        
        print("  자주 등장하는 단어:", dict(word_counter.most_common(15)))
    
    # 과소추정이 심한 케이스 분석
    print("\n\n" + "=" * 90)
    print("과소추정 심한 케이스 (v5 error < -70%) 샘플")
    print("=" * 90)
    
    severe_under = df[df['v5_error'] < -70].sort_values('v5_error').head(20)
    for _, row in severe_under.iterrows():
        print(f"\n실제: {row['actual_weight']:.2f}kg, v5추정: {row['new_weight_kg']:.2f}kg, 오차: {row['v5_error']:.0f}%")
        print(f"  제목: {row['title_origin'][:60]}...")
        print(f"  이유: {row['new_reason']}")
    
    # 과대추정 케이스 분석
    print("\n\n" + "=" * 90)
    print("과대추정 케이스 (v5 error > 50%) 샘플")
    print("=" * 90)
    
    severe_over = df[df['v5_error'] > 50].sort_values('v5_error', ascending=False).head(20)
    for _, row in severe_over.iterrows():
        print(f"\n실제: {row['actual_weight']:.2f}kg, v5추정: {row['new_weight_kg']:.2f}kg, 오차: {row['v5_error']:.0f}%")
        print(f"  제목: {row['title_origin'][:60]}...")
        print(f"  이유: {row['new_reason']}")

if __name__ == "__main__":
    main()
