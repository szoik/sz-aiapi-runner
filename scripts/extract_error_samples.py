#!/usr/bin/env python3
"""
오차 상위 N개 샘플 추출 스크립트

특정 카테고리 데이터셋에서 오차율이 높은 상품의 이미지 URL을 추출합니다.

사용법:
    # 과대추정 상위 5개 추출
    python scripts/extract_error_samples.py -i .local/tmp/category_datasets/robot_toy.tsv --type over -n 5
    
    # 과소추정 상위 5개 추출
    python scripts/extract_error_samples.py -i .local/tmp/category_datasets/robot_toy.tsv --type under -n 5
    
    # 양방향 (절대값 기준) 상위 10개 추출
    python scripts/extract_error_samples.py -i .local/tmp/category_datasets/robot_toy.tsv --type both -n 10

출력:
    - 콘솔에 이미지 URL과 오차 정보 출력
"""

import argparse
from pathlib import Path

import pandas as pd


def extract_samples(filepath: str, error_type: str, n: int) -> pd.DataFrame:
    """오차 상위 N개 샘플 추출"""
    df = pd.read_csv(filepath, sep='\t')
    
    if error_type == 'over':
        # 과대추정: 양수 오차 중 가장 큰 것
        filtered = df[df['weight_error'] > 0].copy()
        filtered = filtered.sort_values('weight_error', ascending=False)
    elif error_type == 'under':
        # 과소추정: 음수 오차 중 가장 작은 것 (절대값 큰 것)
        filtered = df[df['weight_error'] < 0].copy()
        filtered = filtered.sort_values('weight_error', ascending=True)
    else:  # both
        # 양방향: 절대값 기준
        df['abs_error'] = df['weight_error'].abs()
        filtered = df.sort_values('abs_error', ascending=False)
    
    return filtered.head(n)


def format_output(samples: pd.DataFrame, error_type: str) -> str:
    """추출 결과를 텍스트로 포맷"""
    lines = []
    
    type_label = {
        'over': '과대추정',
        'under': '과소추정',
        'both': '절대값 기준'
    }
    
    lines.append(f"오차 상위 {len(samples)}개 ({type_label[error_type]})")
    lines.append("-" * 80)
    
    for i, (idx, row) in enumerate(samples.iterrows(), 1):
        ai_kg = row['ai_weight_kg']
        actual_kg = row['actual_weight']
        error = row['weight_error']
        
        if error >= 0:
            error_str = f"+{error:.1%}"
        else:
            error_str = f"{error:.1%}"
        
        lines.append(f"\n{i}) {error_str} (AI: {ai_kg:.2f}kg, 실측: {actual_kg:.2f}kg)")
        lines.append(f"   {row['thumbnail_urls']}")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description='오차 상위 N개 샘플 추출')
    parser.add_argument('--input', '-i', required=True,
                        help='입력 데이터 파일')
    parser.add_argument('--type', '-t', choices=['over', 'under', 'both'], default='both',
                        help='추출 유형: over(과대추정), under(과소추정), both(절대값)')
    parser.add_argument('-n', type=int, default=5,
                        help='추출할 샘플 수 (기본: 5)')
    args = parser.parse_args()
    
    filepath = args.input
    
    if not Path(filepath).exists():
        print(f"파일을 찾을 수 없습니다: {filepath}")
        return
    
    # 샘플 추출
    samples = extract_samples(filepath, args.type, args.n)
    
    # 헤더 출력
    filename = Path(filepath).stem
    print("=" * 80)
    print(f"{filename}")
    print("=" * 80)
    
    if len(samples) == 0:
        print(f"\n해당 조건의 샘플이 없습니다.")
    else:
        print(format_output(samples, args.type))


if __name__ == '__main__':
    main()
