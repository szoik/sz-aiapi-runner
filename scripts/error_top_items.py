#!/usr/bin/env python3
"""
오차 TOP N 항목 추출 스크립트

카테고리별 오차가 가장 큰 항목들을 추출하여 테이블 형식으로 출력합니다.

사용법:
    python scripts/error_top_items.py --input INPUT_FILE [--top N] [--type TYPE] [--output OUTPUT_DIR]

예시:
    # 과대추정 TOP 10 (기본)
    python scripts/error_top_items.py -i inputs/categories/o01_보이그룹_인형피규어_err50.tsv
    
    # 과소추정 TOP 5
    python scripts/error_top_items.py -i inputs/categories/u01_이어폰팁_err50.tsv --top 5 --type under
    
    # 양방향 모두 출력
    python scripts/error_top_items.py -i inputs/dataset_proper.tsv --top 10 --type both

출력:
    - 콘솔에 오차 TOP N 테이블 출력
    - 파일로 저장 (--output 지정시)
"""

import argparse
from pathlib import Path

import pandas as pd


def load_data(input_file: str) -> pd.DataFrame:
    """데이터 로드"""
    df = pd.read_csv(input_file, sep='\t', low_memory=False)
    
    # 숫자 컬럼 변환
    numeric_cols = ['weight_error', 'volume_error', 'ai_weight_kg', 'actual_weight']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df


def format_weight(kg: float) -> str:
    """무게를 적절한 단위로 포맷"""
    if pd.isna(kg):
        return '-'
    grams = kg * 1000
    if grams >= 1000:
        return f'{kg:.1f}kg'
    else:
        return f'{grams:.0f}g'


def format_error(error: float) -> str:
    """오차율 포맷 (부호 포함)"""
    if pd.isna(error):
        return '-'
    pct = error * 100
    if pct >= 0:
        return f'+{pct:.1f}%'
    else:
        return f'{pct:.1f}%'


def get_thumbnail_url(row: pd.Series) -> str:
    """썸네일 URL 추출 (첫 번째 URL)"""
    urls = row.get('thumbnail_urls', '')
    if pd.isna(urls) or not urls:
        return '-'
    # 여러 URL이 있을 경우 첫 번째 반환 (|로 구분됨)
    first_url = str(urls).split('|')[0].strip()
    return first_url if first_url else '-'


def extract_top_items(df: pd.DataFrame, top_n: int, error_type: str = 'over') -> pd.DataFrame:
    """오차 TOP N 항목 추출
    
    Args:
        df: 데이터프레임
        top_n: 추출할 항목 수
        error_type: 'over' (과대추정), 'under' (과소추정)
    
    Returns:
        TOP N 항목 데이터프레임
    """
    # weight_error가 있는 행만 필터링
    valid_df = df[df['weight_error'].notna()].copy()
    
    if error_type == 'over':
        # 과대추정: 오차가 큰 순 (양수 방향)
        sorted_df = valid_df.sort_values('weight_error', ascending=False)
    else:
        # 과소추정: 오차가 작은 순 (음수 방향)
        sorted_df = valid_df.sort_values('weight_error', ascending=True)
    
    return sorted_df.head(top_n)


def print_top_items_table(df: pd.DataFrame, title: str, output_file: str = None):
    """TOP N 항목 테이블 출력"""
    lines = []
    
    lines.append(f'\n{title}')
    lines.append('=' * 80)
    lines.append(f'{"#":<4} {"오차율":<12} {"AI":<10} {"실측":<10} URL')
    lines.append('-' * 80)
    
    for idx, (_, row) in enumerate(df.iterrows(), 1):
        error_str = format_error(row['weight_error'])
        ai_weight = format_weight(row.get('ai_weight_kg'))
        actual_weight = format_weight(row.get('actual_weight'))
        url = get_thumbnail_url(row)
        
        lines.append(f'{idx:<4} {error_str:<12} {ai_weight:<10} {actual_weight:<10} {url}')
    
    lines.append('')
    
    # 콘솔 출력
    for line in lines:
        print(line)
    
    # 파일 저장
    if output_file:
        with open(output_file, 'a', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        print(f'테이블 저장 완료: {output_file}')
    
    return lines


def print_markdown_table(df: pd.DataFrame, title: str, output_file: str = None):
    """마크다운 테이블 형식으로 출력"""
    lines = []
    
    lines.append(f'\n### {title}')
    lines.append('')
    lines.append('| # | 오차율 | AI | 실측 | URL |')
    lines.append('|---|--------|----|----|-----|')
    
    for idx, (_, row) in enumerate(df.iterrows(), 1):
        error_str = format_error(row['weight_error'])
        ai_weight = format_weight(row.get('ai_weight_kg'))
        actual_weight = format_weight(row.get('actual_weight'))
        url = get_thumbnail_url(row)
        
        lines.append(f'| {idx} | {error_str} | {ai_weight} | {actual_weight} | {url} |')
    
    lines.append('')
    
    # 콘솔 출력
    for line in lines:
        print(line)
    
    # 파일 저장
    if output_file:
        with open(output_file, 'a', encoding='utf-8') as f:
            f.write('\n'.join(lines))
    
    return lines


def main():
    parser = argparse.ArgumentParser(description='오차 TOP N 항목 추출')
    parser.add_argument('--input', '-i', required=True,
                        help='입력 데이터 파일 (TSV)')
    parser.add_argument('--top', '-n', type=int, default=10,
                        help='추출할 항목 수 (기본: 10)')
    parser.add_argument('--type', '-t', choices=['over', 'under', 'both'], default='both',
                        help='오차 유형: over(과대), under(과소), both(양쪽) (기본: both)')
    parser.add_argument('--output', '-o', default=None,
                        help='출력 디렉토리 (기본: 콘솔만 출력)')
    parser.add_argument('--format', '-f', choices=['text', 'markdown'], default='text',
                        help='출력 형식: text, markdown (기본: text)')
    args = parser.parse_args()
    
    # 경로 설정
    script_dir = Path(__file__).parent.parent
    input_file = script_dir / args.input
    
    # 데이터 로드
    print(f'데이터 로드 중: {input_file}')
    df = load_data(input_file)
    print(f'총 {len(df):,}건 로드됨\n')
    
    # 출력 파일 설정
    output_file = None
    if args.output:
        output_dir = script_dir / args.output
        output_dir.mkdir(parents=True, exist_ok=True)
        ext = '.md' if args.format == 'markdown' else '.txt'
        output_file = output_dir / f'error_top{args.top}_items{ext}'
        # 기존 파일 초기화
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f'# 오차 TOP {args.top} 항목\n')
            f.write(f'입력 파일: {args.input}\n')
            f.write(f'총 데이터: {len(df):,}건\n')
    
    # 입력 파일명에서 카테고리 추출
    category_name = Path(args.input).stem
    
    # 테이블 출력 함수 선택
    print_func = print_markdown_table if args.format == 'markdown' else print_top_items_table
    
    # 과대추정 TOP N
    if args.type in ['over', 'both']:
        over_df = extract_top_items(df, args.top, 'over')
        print_func(over_df, f'과대추정 TOP {args.top} ({category_name})', output_file)
    
    # 과소추정 TOP N
    if args.type in ['under', 'both']:
        under_df = extract_top_items(df, args.top, 'under')
        print_func(under_df, f'과소추정 TOP {args.top} ({category_name})', output_file)


if __name__ == '__main__':
    main()
