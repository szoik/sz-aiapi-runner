#!/usr/bin/env python3
"""
카테고리별 오차 패턴 분석 스크립트

특정 카테고리 데이터셋의 오차 패턴을 분석합니다.
- 오차 방향성 (과대/과소/양방향)
- AI 추정값 패턴 (고정값 의존 여부)
- 실측값 분포
- AI-실측 상관관계

사용법:
    # 단일 파일 분석
    python scripts/category_pattern_analysis.py -i .local/tmp/category_datasets/robot_toy.tsv
    
    # 여러 파일 분석
    python scripts/category_pattern_analysis.py -i .local/tmp/category_datasets/*.tsv
    
    # 결과를 파일로 저장
    python scripts/category_pattern_analysis.py -i .local/tmp/category_datasets/*.tsv -o .local/tmp/pattern_analysis.txt

출력:
    - 콘솔에 패턴 분석 결과 출력
    - -o 옵션 사용 시 파일로 저장
"""

import argparse
import sys
from glob import glob
from pathlib import Path

import pandas as pd


def analyze_category(filepath: str) -> dict:
    """단일 카테고리 파일 분석"""
    df = pd.read_csv(filepath, sep='\t')
    
    total = len(df)
    ai_weight = df['ai_weight_kg']
    actual_weight = df['actual_weight']
    weight_error = df['weight_error']
    
    # 오차 구간별 건수
    over_count = (weight_error > 0.5).sum()
    under_count = (weight_error < -0.5).sum()
    accurate_count = ((weight_error >= -0.1) & (weight_error <= 0.1)).sum()
    
    # AI 추정값 최빈값
    ai_value_counts = ai_weight.value_counts()
    top_ai_value = ai_value_counts.index[0] if len(ai_value_counts) > 0 else None
    top_ai_pct = ai_value_counts.iloc[0] / total * 100 if len(ai_value_counts) > 0 else 0
    
    # 상관계수
    corr = ai_weight.corr(actual_weight)
    
    # 패턴 판단
    if over_count > under_count * 2:
        error_direction = "과대추정 우세"
    elif under_count > over_count * 2:
        error_direction = "과소추정 우세"
    else:
        error_direction = "양방향 오차"
    
    if top_ai_pct > 60:
        ai_pattern = f"고정값 의존 ({top_ai_value:.1f}kg = {top_ai_pct:.0f}%)"
    else:
        ai_pattern = "다양한 추정값"
    
    if corr > 0.5:
        corr_level = "높음"
    elif corr > 0.3:
        corr_level = "중간"
    else:
        corr_level = "낮음"
    
    return {
        'filepath': filepath,
        'filename': Path(filepath).stem,
        'total': total,
        'over_count': over_count,
        'over_pct': over_count / total * 100,
        'under_count': under_count,
        'under_pct': under_count / total * 100,
        'accurate_count': accurate_count,
        'accurate_pct': accurate_count / total * 100,
        'error_mean': weight_error.mean(),
        'error_median': weight_error.median(),
        'error_std': weight_error.std(),
        'ai_top_value': top_ai_value,
        'ai_top_pct': top_ai_pct,
        'ai_value_counts': ai_value_counts.head(5),
        'ai_min': ai_weight.min(),
        'ai_max': ai_weight.max(),
        'actual_mean': actual_weight.mean(),
        'actual_median': actual_weight.median(),
        'actual_min': actual_weight.min(),
        'actual_max': actual_weight.max(),
        'actual_q1': actual_weight.quantile(0.25),
        'actual_q3': actual_weight.quantile(0.75),
        'correlation': corr,
        'error_direction': error_direction,
        'ai_pattern': ai_pattern,
        'corr_level': corr_level,
    }


def format_report(result: dict) -> str:
    """분석 결과를 텍스트 리포트로 포맷"""
    lines = []
    lines.append("=" * 80)
    lines.append(f"{result['filename']}")
    lines.append("=" * 80)
    
    lines.append(f"\n[1] 기본 현황")
    lines.append(f"    총 건수: {result['total']}")
    lines.append(f"    과대추정(+50%↑): {result['over_count']} ({result['over_pct']:.1f}%)")
    lines.append(f"    과소추정(-50%↓): {result['under_count']} ({result['under_pct']:.1f}%)")
    lines.append(f"    정확(-10%~+10%): {result['accurate_count']} ({result['accurate_pct']:.1f}%)")
    
    lines.append(f"\n[2] 오차율 분포")
    lines.append(f"    평균: {result['error_mean']*100:+.1f}%")
    lines.append(f"    중앙값: {result['error_median']*100:+.1f}%")
    lines.append(f"    표준편차: {result['error_std']*100:.1f}%")
    
    lines.append(f"\n[3] AI 추정값 패턴")
    lines.append(f"    최빈값 TOP 5:")
    for val, cnt in result['ai_value_counts'].items():
        lines.append(f"      {val:.1f}kg: {cnt}건 ({cnt/result['total']*100:.1f}%)")
    lines.append(f"    범위: {result['ai_min']:.2f}kg ~ {result['ai_max']:.1f}kg")
    
    lines.append(f"\n[4] 실측값 분포")
    lines.append(f"    평균: {result['actual_mean']:.2f}kg ({result['actual_mean']*1000:.0f}g)")
    lines.append(f"    중앙값: {result['actual_median']:.2f}kg ({result['actual_median']*1000:.0f}g)")
    lines.append(f"    범위: {result['actual_min']:.2f}kg ~ {result['actual_max']:.2f}kg")
    lines.append(f"    사분위: Q1={result['actual_q1']:.2f}kg, Q3={result['actual_q3']:.2f}kg")
    
    lines.append(f"\n[5] AI-실측 상관계수: {result['correlation']:.3f}")
    
    lines.append(f"\n[6] 패턴 요약")
    lines.append(f"    오차 방향: {result['error_direction']}")
    lines.append(f"    AI 패턴: {result['ai_pattern']}")
    lines.append(f"    상관성: {result['corr_level']} ({result['correlation']:.2f})")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description='카테고리별 오차 패턴 분석')
    parser.add_argument('--input', '-i', required=True, nargs='+',
                        help='입력 데이터 파일 (glob 패턴 지원)')
    parser.add_argument('--output', '-o', default=None,
                        help='출력 파일 경로 (미지정 시 콘솔 출력)')
    args = parser.parse_args()
    
    # 입력 파일 목록 확장 (glob 패턴 처리)
    input_files = []
    for pattern in args.input:
        matched = glob(pattern)
        if matched:
            input_files.extend(matched)
        else:
            input_files.append(pattern)
    
    # 중복 제거 및 정렬
    input_files = sorted(set(input_files))
    
    if not input_files:
        print("분석할 파일이 없습니다.", file=sys.stderr)
        sys.exit(1)
    
    # 분석 실행
    output_lines = []
    output_lines.append("=" * 80)
    output_lines.append("카테고리별 오차 패턴 분석")
    output_lines.append("=" * 80)
    
    results = []
    for filepath in input_files:
        try:
            result = analyze_category(filepath)
            results.append(result)
            output_lines.append("")
            output_lines.append(format_report(result))
        except Exception as e:
            output_lines.append(f"\n오류: {filepath} - {e}")
    
    # 요약 테이블
    if len(results) > 1:
        output_lines.append("\n")
        output_lines.append("=" * 80)
        output_lines.append("요약 테이블")
        output_lines.append("=" * 80)
        output_lines.append(f"\n{'카테고리':<30} {'건수':>6} {'오차방향':<12} {'AI패턴':<25} {'상관계수':>8}")
        output_lines.append("-" * 90)
        for r in results:
            output_lines.append(
                f"{r['filename']:<30} {r['total']:>6} {r['error_direction']:<12} "
                f"{r['ai_pattern']:<25} {r['correlation']:>8.2f}"
            )
    
    # 출력
    output_text = "\n".join(output_lines)
    
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output_text, encoding='utf-8')
        print(f"분석 결과 저장: {args.output}")
    else:
        print(output_text)


if __name__ == '__main__':
    main()
