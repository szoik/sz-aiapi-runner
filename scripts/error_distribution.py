#!/usr/bin/env python3
"""
오차 구간별 분포 분석 스크립트

AI 추정값과 실측값 간의 오차를 구간별로 분석하고 시각화합니다.
분석 대상: Max Dim, Mid Dim, Min Dim, Volume, Weight

사용법:
    python scripts/error_distribution.py [--input INPUT_FILE] [--name NAME]

예시:
    # 기본 실행 (datasource_complete.tsv)
    python scripts/error_distribution.py
    
    # 특정 카테고리 분석
    python scripts/error_distribution.py -i inputs/categories/o01_보이그룹_인형피규어_err50.tsv
    
    # 커스텀 이름 지정
    python scripts/error_distribution.py -i inputs/datasource_complete.tsv --name baseline

출력 경로: artifacts/dataset_analysis/vw-{serial}-{dataset명}/
    - error_distribution.png: 오차 분포 시각화
    - error_distribution_summary.csv: 요약 테이블
    - error_distribution.txt: 상세 분포 테이블
    - meta.json: 메타 정보
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np


def get_project_root() -> Path:
    """Get project root directory."""
    return Path(__file__).parent.parent


def get_dataset_analysis_dir() -> Path:
    """Get dataset analysis output directory."""
    return get_project_root() / "artifacts" / "dataset_analysis"


def get_next_serial(analysis_dir: Path) -> int:
    """Get next serial number by scanning existing analysis directories."""
    if not analysis_dir.exists():
        return 1
    
    max_serial = 0
    pattern = re.compile(r"(?:[\w]+-)?(\d{3})-")
    
    for item in analysis_dir.iterdir():
        if item.is_dir():
            match = pattern.match(item.name)
            if match:
                serial = int(match.group(1))
                max_serial = max(max_serial, serial)
    
    return max_serial + 1


def extract_dataset_name(input_file: Path) -> str:
    """Extract dataset name from input file path."""
    return input_file.stem


def generate_analysis_id(analysis_dir: Path, input_file: Path, name: str = None) -> str:
    """Generate analysis ID like vw-001-datasource_complete."""
    serial = get_next_serial(analysis_dir)
    dataset = extract_dataset_name(input_file)
    
    if name:
        return f"{name}-{serial:03d}-{dataset}"
    else:
        return f"vw-{serial:03d}-{dataset}"


def save_meta(output_dir: Path, input_file: Path, analysis_id: str):
    """Save meta.json with analysis information."""
    meta = {
        "analysis_id": analysis_id,
        "input_file": str(input_file),
        "created_at": datetime.now().isoformat(),
        "type": "dataset_analysis"
    }
    
    meta_path = output_dir / "meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    
    print(f"메타 정보 저장: {meta_path}")

# 한글 폰트 설정 (macOS)
plt.rcParams['font.family'] = ['AppleGothic', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


# 오차 구간 정의
ERROR_BINS = [
    (-float('inf'), -1.0, '< -100%'),
    (-1.0, -0.9, '-100%~-90%'),
    (-0.9, -0.8, '-90%~-80%'),
    (-0.8, -0.7, '-80%~-70%'),
    (-0.7, -0.6, '-70%~-60%'),
    (-0.6, -0.5, '-60%~-50%'),
    (-0.5, -0.4, '-50%~-40%'),
    (-0.4, -0.3, '-40%~-30%'),
    (-0.3, -0.2, '-30%~-20%'),
    (-0.2, -0.1, '-20%~-10%'),
    (-0.1, 0.0, '-10%~0%'),
    (0.0, 0.1, '0%~+10%'),
    (0.1, 0.2, '+10%~+20%'),
    (0.2, 0.3, '+20%~+30%'),
    (0.3, 0.4, '+30%~+40%'),
    (0.4, 0.5, '+40%~+50%'),
    (0.5, 0.6, '+50%~+60%'),
    (0.6, 0.7, '+60%~+70%'),
    (0.7, 0.8, '+70%~+80%'),
    (0.8, 0.9, '+80%~+90%'),
    (0.9, 1.0, '+90%~+100%'),
    (1.0, float('inf'), '> +100%'),
]

# 분석 대상 컬럼
ERROR_COLUMNS = [
    ('max_dim_error', 'Max Dim (최대 치수)'),
    ('mid_dim_error', 'Mid Dim (중간 치수)'),
    ('min_dim_error', 'Min Dim (최소 치수)'),
    ('volume_error', 'Volume (부피)'),
    ('weight_error', 'Weight (무게)'),
]


def load_data(input_file: str) -> pd.DataFrame:
    """데이터 로드 및 오차 컬럼 계산"""
    df = pd.read_csv(input_file, sep='\t', low_memory=False)
    
    # 숫자 컬럼 변환 (문자열로 읽힐 수 있음)
    numeric_cols = ['ai_max', 'ai_mid', 'ai_min', 'actual_max', 'actual_mid', 'actual_min',
                    'weight_error', 'volume_error']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # 치수 오차 계산: (AI - Actual) / Actual
    df['max_dim_error'] = (df['ai_max'] - df['actual_max']) / df['actual_max']
    df['mid_dim_error'] = (df['ai_mid'] - df['actual_mid']) / df['actual_mid']
    df['min_dim_error'] = (df['ai_min'] - df['actual_min']) / df['actual_min']
    
    return df


def get_distribution(series: pd.Series) -> tuple:
    """오차 시리즈의 구간별 분포 계산"""
    valid = series.dropna()
    total = len(valid)
    
    results = []
    for low, high, label in ERROR_BINS:
        if low == -float('inf'):
            count = int((valid < high).sum())
        elif high == float('inf'):
            count = int((valid >= low).sum())
        else:
            count = int(((valid >= low) & (valid < high)).sum())
        pct = count / total * 100 if total > 0 else 0
        results.append((label, count, pct))
    
    stats = {
        'total': total,
        'mean': float(valid.mean()),
        'median': float(valid.median()),
        'std': float(valid.std()),
    }
    
    return results, stats


def print_distribution(df: pd.DataFrame, output_file: str = None):
    """콘솔에 분포 테이블 출력 및 파일 저장"""
    lines = []
    
    lines.append(f"총 데이터: {len(df):,}건")
    lines.append("")
    
    for col, name in ERROR_COLUMNS:
        dist, stats = get_distribution(df[col])
        
        lines.append('=' * 60)
        lines.append(f'{name} 오차 분포')
        lines.append('=' * 60)
        lines.append(f"유효: {stats['total']:,}건 | "
              f"평균: {stats['mean']:.1%} | "
              f"중앙값: {stats['median']:.1%} | "
              f"표준편차: {stats['std']:.1%}")
        lines.append("")
        lines.append(f"{'구간':<15} {'건수':>10} {'비율':>8}")
        lines.append('-' * 40)
        
        for label, count, pct in dist:
            bar = '*' * int(pct / 2)
            lines.append(f"{label:<15} {count:>10,} {pct:>7.1f}% {bar}")
        lines.append("")
    
    # 콘솔 출력
    for line in lines:
        print(line)
    
    # 파일 저장
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        print(f"분포 테이블 저장 완료: {output_file}")


def create_visualization(df: pd.DataFrame, output_path: str, title: str = None):
    """오차 분포 시각화 이미지 생성"""
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    axes = axes.flatten()
    
    # 구간 라벨 (간략화)
    bin_labels = [b[2] for b in ERROR_BINS]
    
    colors = {
        'negative': '#e74c3c',  # 빨강 (과소추정)
        'zero': '#2ecc71',      # 초록 (정확)
        'positive': '#3498db',  # 파랑 (과대추정)
    }
    
    for idx, (col, name) in enumerate(ERROR_COLUMNS):
        ax = axes[idx]
        dist, stats = get_distribution(df[col])
        
        percentages = [d[2] for d in dist]
        
        # 색상 지정: 과소추정(빨강), 정확(초록, -10%~+10%), 과대추정(파랑)
        bar_colors = []
        for i, (low, high, _) in enumerate(ERROR_BINS):
            if low >= -0.1 and high <= 0.1:
                bar_colors.append(colors['zero'])
            elif high <= 0:
                bar_colors.append(colors['negative'])
            else:
                bar_colors.append(colors['positive'])
        
        bars = ax.bar(range(len(bin_labels)), percentages, color=bar_colors, edgecolor='white', linewidth=0.5)
        
        ax.set_title(f'{name}\n평균: {stats["mean"]:.1%} | 중앙값: {stats["median"]:.1%}', 
                     fontsize=12, fontweight='bold')
        ax.set_xlabel('오차 구간')
        ax.set_ylabel('비율 (%)')
        ax.set_xticks(range(len(bin_labels)))
        ax.set_xticklabels(bin_labels, rotation=45, ha='right', fontsize=8)
        ax.set_ylim(0, max(percentages) * 1.1 if percentages else 10)
        
        # 그리드
        ax.yaxis.grid(True, alpha=0.3)
        ax.set_axisbelow(True)
    
    # 마지막 subplot에 범례 추가
    axes[5].axis('off')
    legend_elements = [
        plt.Rectangle((0, 0), 1, 1, facecolor=colors['negative'], label='과소추정 (AI < 실측)'),
        plt.Rectangle((0, 0), 1, 1, facecolor=colors['zero'], label='정확 (-10% ~ +10%)'),
        plt.Rectangle((0, 0), 1, 1, facecolor=colors['positive'], label='과대추정 (AI > 실측)'),
    ]
    axes[5].legend(handles=legend_elements, loc='center', fontsize=14)
    
    # 요약 텍스트
    summary_text = f"""
    총 데이터: {len(df):,}건
    
    오차 = (AI추정 - 실측) / 실측
    
    음수(-): AI가 실제보다 작게 추정
    양수(+): AI가 실제보다 크게 추정
    """
    axes[5].text(0.5, 0.3, summary_text, transform=axes[5].transAxes,
                 fontsize=11, verticalalignment='center', horizontalalignment='center',
                 bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    # 차트 제목 설정
    main_title = f'AI 추정 오차 구간별 분포'
    if title:
        main_title = f'{title}\n{main_title}'
    plt.suptitle(main_title, fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f"시각화 저장 완료: {output_path}")


def create_summary_table(df: pd.DataFrame, output_path: str):
    """요약 테이블 CSV 저장"""
    rows = []
    for col, name in ERROR_COLUMNS:
        dist, stats = get_distribution(df[col])
        
        row = {
            '지표': name,
            '유효 데이터': stats['total'],
            '평균 오차': f"{stats['mean']:.1%}",
            '중앙값 오차': f"{stats['median']:.1%}",
            '표준편차': f"{stats['std']:.1%}",
        }
        
        # 주요 구간 비율 추가
        for label, count, pct in dist:
            row[label] = f"{pct:.1f}%"
        
        rows.append(row)
    
    summary_df = pd.DataFrame(rows)
    summary_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"요약 테이블 저장 완료: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='오차 구간별 분포 분석')
    parser.add_argument('--input', '-i', default='inputs/datasource_complete.tsv',
                        help='입력 데이터 파일 (기본: inputs/datasource_complete.tsv)')
    parser.add_argument('--name', '-n', default=None,
                        help='분석 이름 접두어 (기본: vw)')
    args = parser.parse_args()
    
    # 경로 설정
    project_root = get_project_root()
    input_file = project_root / args.input
    
    if not input_file.exists():
        print(f"오류: 입력 파일을 찾을 수 없습니다: {input_file}")
        return
    
    # 출력 디렉토리 설정
    analysis_dir = get_dataset_analysis_dir()
    analysis_id = generate_analysis_id(analysis_dir, input_file, args.name)
    output_dir = analysis_dir / analysis_id
    
    # 출력 디렉토리 생성
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"분석 ID: {analysis_id}")
    print(f"출력 경로: {output_dir}")
    
    # 제목 설정 (입력 파일명에서 추출)
    chart_title = extract_dataset_name(input_file)
    
    # 데이터 로드
    print(f"데이터 로드 중: {input_file}")
    df = load_data(input_file)
    
    # 메타 정보 저장
    save_meta(output_dir, input_file, analysis_id)
    
    # 콘솔 출력 및 텍스트 파일 저장
    print_distribution(df, output_dir / 'error_distribution.txt')
    
    # 시각화 저장
    create_visualization(df, output_dir / 'error_distribution.png', chart_title)
    
    # 요약 테이블 저장
    create_summary_table(df, output_dir / 'error_distribution_summary.csv')
    
    print(f"\n다음 단계:")
    print(f"  결과 확인: open {output_dir}")


if __name__ == '__main__':
    main()
