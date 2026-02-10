#!/usr/bin/env python3
"""
중복 데이터셋 실측치 변동성 분석 스크립트

동일한 상품(이미지)이 여러 번 배송될 때 실측치가 얼마나 다른지 분석합니다.
AI 추정치는 동일한데 실측치는 다른 경우를 시각화합니다.

사용법:
    python scripts/dataset_analysis/actual_value_variability.py [--input INPUT_FILE] [--output OUTPUT_DIR] [--title TITLE]

출력:
    - 상품별 실측치 분포 boxplot (actual_variability.png)
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# 한글 폰트 설정 (macOS)
plt.rcParams['font.family'] = ['AppleGothic', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def load_data(input_file: str) -> pd.DataFrame:
    """데이터 로드"""
    return pd.read_csv(input_file, sep='\t')


def analyze_variability(df: pd.DataFrame):
    """상품별 실측치 변동성 분석"""
    # thumbnail_urls 기준으로 그룹화
    grouped = df.groupby('thumbnail_urls')
    
    results = []
    for url, group in grouped:
        if len(group) < 2:
            continue
        
        title = str(group.iloc[0]['title_origin'])[:30]
        
        result = {
            'thumbnail_urls': url,
            'title': title,
            'count': len(group),
            # AI 추정치 (동일해야 함)
            'ai_weight': group['ai_weight_kg'].iloc[0],
            'ai_max': group['ai_max'].iloc[0],
            'ai_mid': group['ai_mid'].iloc[0],
            'ai_min': group['ai_min'].iloc[0],
            # 실측치 통계
            'actual_weight_min': group['actual_weight'].min(),
            'actual_weight_max': group['actual_weight'].max(),
            'actual_weight_mean': group['actual_weight'].mean(),
            'actual_weight_std': group['actual_weight'].std(),
            'actual_max_min': group['actual_max'].min(),
            'actual_max_max': group['actual_max'].max(),
            'actual_mid_min': group['actual_mid'].min(),
            'actual_mid_max': group['actual_mid'].max(),
            'actual_min_min': group['actual_min'].min(),
            'actual_min_max': group['actual_min'].max(),
        }
        
        # 변동 범위 계산
        result['weight_range'] = result['actual_weight_max'] - result['actual_weight_min']
        result['weight_range_pct'] = result['weight_range'] / result['actual_weight_mean'] * 100 if result['actual_weight_mean'] > 0 else 0
        
        results.append(result)
    
    return pd.DataFrame(results)


def create_visualization(df: pd.DataFrame, variability_df: pd.DataFrame, output_path: str, title: str = None):
    """실측치 변동성 시각화"""
    
    # 중복 횟수 상위 15개 상품 선택
    top_products = variability_df.nlargest(15, 'count')
    
    if len(top_products) == 0:
        print("시각화할 중복 데이터가 없습니다.")
        return
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 14))
    
    # 색상
    colors = {
        'actual': '#3498db',
        'ai': '#e74c3c',
    }
    
    # 1. 무게 변동성 (boxplot)
    ax1 = axes[0, 0]
    weight_data = []
    labels = []
    ai_weights = []
    
    for _, row in top_products.iterrows():
        url = row['thumbnail_urls']
        product_data = df[df['thumbnail_urls'] == url]['actual_weight'].values
        weight_data.append(product_data)
        labels.append(row['title'][:20] + '...' if len(row['title']) > 20 else row['title'])
        ai_weights.append(row['ai_weight'])
    
    bp = ax1.boxplot(weight_data, vert=True, patch_artist=True)
    for patch in bp['boxes']:
        patch.set_facecolor(colors['actual'])
        patch.set_alpha(0.7)
    
    # AI 추정치 표시 (빨간 점)
    for i, ai_w in enumerate(ai_weights):
        ax1.scatter(i + 1, ai_w, color=colors['ai'], s=100, zorder=5, marker='D', label='AI 추정' if i == 0 else '')
    
    ax1.set_xticklabels(labels, rotation=45, ha='right', fontsize=9)
    ax1.set_ylabel('무게 (kg)')
    ax1.set_title('상품별 실측 무게 분포 vs AI 추정치', fontweight='bold')
    ax1.legend(loc='upper right')
    ax1.yaxis.grid(True, alpha=0.3)
    
    # 2. Max 치수 변동성
    ax2 = axes[0, 1]
    max_data = []
    ai_maxs = []
    
    for _, row in top_products.iterrows():
        url = row['thumbnail_urls']
        product_data = df[df['thumbnail_urls'] == url]['actual_max'].values
        max_data.append(product_data)
        ai_maxs.append(row['ai_max'])
    
    bp = ax2.boxplot(max_data, vert=True, patch_artist=True)
    for patch in bp['boxes']:
        patch.set_facecolor(colors['actual'])
        patch.set_alpha(0.7)
    
    for i, ai_m in enumerate(ai_maxs):
        ax2.scatter(i + 1, ai_m, color=colors['ai'], s=100, zorder=5, marker='D')
    
    ax2.set_xticklabels(labels, rotation=45, ha='right', fontsize=9)
    ax2.set_ylabel('Max 치수 (cm)')
    ax2.set_title('상품별 실측 Max 치수 분포 vs AI 추정치', fontweight='bold')
    ax2.yaxis.grid(True, alpha=0.3)
    
    # 3. 무게 변동 범위 (%)
    ax3 = axes[1, 0]
    variability_df_sorted = variability_df.nlargest(20, 'weight_range_pct')
    
    bars = ax3.barh(range(len(variability_df_sorted)), variability_df_sorted['weight_range_pct'], color=colors['actual'], alpha=0.7)
    ax3.set_yticks(range(len(variability_df_sorted)))
    ax3.set_yticklabels([t[:25] + '...' if len(t) > 25 else t for t in variability_df_sorted['title']], fontsize=9)
    ax3.set_xlabel('무게 변동 범위 (%)')
    ax3.set_title('상품별 무게 변동률 (상위 20개)', fontweight='bold')
    ax3.xaxis.grid(True, alpha=0.3)
    ax3.invert_yaxis()
    
    # 4. 요약 통계
    ax4 = axes[1, 1]
    ax4.axis('off')
    
    summary_text = f"""
    중복 데이터 요약
    ─────────────────────────────
    
    총 중복 상품 종류: {len(variability_df)}개
    총 중복 건수: {variability_df['count'].sum()}건
    
    무게 변동성:
      • 평균 변동 범위: {variability_df['weight_range'].mean():.2f} kg
      • 최대 변동 범위: {variability_df['weight_range'].max():.2f} kg
      • 평균 변동률: {variability_df['weight_range_pct'].mean():.1f}%
    
    AI 추정 특성:
      • 동일 이미지 → 동일 추정치 (변동 없음)
      • 실측치는 배송마다 다름 (포장 차이)
    
    ─────────────────────────────
    
    🔵 파란색 박스: 실측치 분포
    🔴 빨간색 다이아몬드: AI 추정치
    """
    
    ax4.text(0.1, 0.5, summary_text, transform=ax4.transAxes,
             fontsize=12, verticalalignment='center', horizontalalignment='left',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    # 전체 제목
    main_title = '중복 상품 실측치 변동성 분석'
    if title:
        main_title = f'{title}\n{main_title}'
    plt.suptitle(main_title, fontsize=16, fontweight='bold', y=1.02)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f"시각화 저장 완료: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='중복 데이터셋 실측치 변동성 분석')
    parser.add_argument('--input', '-i', required=True,
                        help='입력 데이터 파일 (중복 데이터셋)')
    parser.add_argument('--output', '-o', required=True,
                        help='출력 디렉토리')
    parser.add_argument('--title', '-t', default=None,
                        help='차트 제목')
    args = parser.parse_args()
    
    # 경로 설정
    from common import PROJECT_ROOT
    input_file = PROJECT_ROOT / args.input
    output_dir = PROJECT_ROOT / args.output
    
    # 출력 디렉토리 생성
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 데이터 로드
    print(f"데이터 로드 중: {input_file}")
    df = load_data(input_file)
    print(f"총 데이터: {len(df):,}건")
    
    # 변동성 분석
    variability_df = analyze_variability(df)
    print(f"중복 상품 종류: {len(variability_df)}개")
    
    if len(variability_df) == 0:
        print("중복 데이터가 없습니다.")
        return
    
    # 콘솔 출력
    print()
    print("=== 변동성 상위 10개 상품 ===")
    top10 = variability_df.nlargest(10, 'weight_range_pct')
    for _, row in top10.iterrows():
        print(f"{row['count']:>3}건 | "
              f"무게: {row['actual_weight_min']:.2f}~{row['actual_weight_max']:.2f}kg (AI: {row['ai_weight']:.2f}kg) | "
              f"변동률: {row['weight_range_pct']:.1f}% | "
              f"{row['title']}")
    
    # 시각화 저장
    create_visualization(df, variability_df, output_dir / 'actual_variability.png', args.title)
    
    # 변동성 데이터 저장
    variability_df.to_csv(output_dir / 'variability_summary.csv', index=False, encoding='utf-8-sig')
    print(f"변동성 요약 저장 완료: {output_dir / 'variability_summary.csv'}")


if __name__ == '__main__':
    main()
