#!/usr/bin/env python3
"""
Error Analysis - Weight & Volume Predictions

Converted from colab/05_error_analysis.ipynb for local execution.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import argparse
from pathlib import Path

OUTPUT_DIR = Path('.local/tmp/error_analysis')


def setup_korean_font():
    """Setup Korean font for matplotlib."""
    # Try common Korean fonts on macOS
    korean_fonts = [
        'AppleGothic',
        'Apple SD Gothic Neo',
        'NanumGothic',
        'Malgun Gothic',
    ]
    
    available_fonts = [f.name for f in fm.fontManager.ttflist]
    
    for font in korean_fonts:
        if font in available_fonts:
            plt.rcParams['font.family'] = font
            plt.rcParams['axes.unicode_minus'] = False
            print(f"Using font: {font}")
            return
    
    print("Warning: No Korean font found, characters may not display correctly")


def load_data(filepath: str) -> pd.DataFrame:
    df = pd.read_csv(filepath, sep='\t')
    print(f"Loaded {len(df)} rows")
    return df


def analyze_error_overview(df: pd.DataFrame):
    print("\n" + "="*60)
    print("ERROR OVERVIEW")
    print("="*60)
    error_cols = ['weight_error', 'volume_error', 'max_error', 'mid_error', 'min_error', 'avg_dim_error']
    available_cols = [c for c in error_cols if c in df.columns]
    print(df[available_cols].describe())


def analyze_top_volume_errors(df: pd.DataFrame):
    print("\n" + "="*60)
    print("TOP 200 VOLUME ERRORS")
    print("="*60)

    cols = ['product_version_id', 'title_origin', 'category', 'volume_error', 'weight_error',
            'actual_volume_cm3', 'ai_volume_cm3', 'thumbnail_urls']
    cols = [c for c in cols if c in df.columns]

    top_positive = df.nlargest(200, 'volume_error')[cols]
    print(f"\nPOSITIVE Volume Errors (AI overestimated)")
    print(f"Error range: {top_positive['volume_error'].min():.2%} ~ {top_positive['volume_error'].max():.2%}")
    top_positive.to_csv(OUTPUT_DIR / 'top200_volume_error_positive.tsv', sep='\t', index=False)

    top_negative = df.nsmallest(200, 'volume_error')[cols]
    print(f"\nNEGATIVE Volume Errors (AI underestimated)")
    print(f"Error range: {top_negative['volume_error'].min():.2%} ~ {top_negative['volume_error'].max():.2%}")
    top_negative.to_csv(OUTPUT_DIR / 'top200_volume_error_negative.tsv', sep='\t', index=False)


def analyze_top_weight_errors(df: pd.DataFrame):
    print("\n" + "="*60)
    print("TOP 200 WEIGHT ERRORS")
    print("="*60)

    cols = ['product_version_id', 'title_origin', 'category', 'weight_error', 'volume_error',
            'actual_weight', 'ai_weight_kg', 'thumbnail_urls']
    cols = [c for c in cols if c in df.columns]

    top_positive = df.nlargest(200, 'weight_error')[cols]
    print(f"\nPOSITIVE Weight Errors (AI overestimated)")
    print(f"Error range: {top_positive['weight_error'].min():.2%} ~ {top_positive['weight_error'].max():.2%}")
    top_positive.to_csv(OUTPUT_DIR / 'top200_weight_error_positive.tsv', sep='\t', index=False)

    top_negative = df.nsmallest(200, 'weight_error')[cols]
    print(f"\nNEGATIVE Weight Errors (AI underestimated)")
    print(f"Error range: {top_negative['weight_error'].min():.2%} ~ {top_negative['weight_error'].max():.2%}")
    top_negative.to_csv(OUTPUT_DIR / 'top200_weight_error_negative.tsv', sep='\t', index=False)


def analyze_combined_errors(df: pd.DataFrame):
    print("\n" + "="*60)
    print("TOP 200 COMBINED ERRORS")
    print("="*60)

    df['combined_error'] = (df['weight_error'].abs() + df['volume_error'].abs()) / 2
    top_combined = df.nlargest(200, 'combined_error')
    print(f"Combined error range: {top_combined['combined_error'].min():.2%} ~ {top_combined['combined_error'].max():.2%}")
    top_combined.to_csv(OUTPUT_DIR / 'top200_combined_error.tsv', sep='\t', index=False)


def analyze_dimension_twist(df: pd.DataFrame):
    print("\n" + "="*60)
    print("DIMENSION TWIST ANALYSIS")
    print("="*60)

    def check_twist(row):
        actual = [row['actual_max'], row['actual_mid'], row['actual_min']]
        ai = [row['ai_max'], row['ai_mid'], row['ai_min']]
        if any(pd.isna(actual)) or any(pd.isna(ai)):
            return 'unknown'
        ratios = [ai[i] / actual[i] if actual[i] > 0 else 0 for i in range(3)]
        return 'twisted' if np.std(ratios) > 0.5 else 'normal'

    df['dim_twist'] = df.apply(check_twist, axis=1)
    print(df['dim_twist'].value_counts())

    twisted = df[df['dim_twist'] == 'twisted']
    print(f"\nTwisted items: {len(twisted)}")
    twisted.to_csv(OUTPUT_DIR / 'twisted_dimensions.tsv', sep='\t', index=False)


def analyze_error_distribution(df: pd.DataFrame):
    print("\n" + "="*60)
    print("ERROR DISTRIBUTION")
    print("="*60)

    def categorize(error):
        abs_err = abs(error)
        if abs_err > 1.0: return 'over_100%'
        elif abs_err > 0.5: return '50%_to_100%'
        elif abs_err > 0.1: return '10%_to_50%'
        else: return 'under_10%'

    df['weight_error_level'] = df['weight_error'].apply(categorize)
    df['volume_error_level'] = df['volume_error'].apply(categorize)

    print("\nWeight Error Distribution:")
    print(df['weight_error_level'].value_counts())
    print("\nVolume Error Distribution:")
    print(df['volume_error_level'].value_counts())
    return df


def analyze_category_stats(df: pd.DataFrame):
    print("\n" + "="*60)
    print("CATEGORY STATISTICS")
    print("="*60)

    df['abs_weight_error'] = df['weight_error'].abs()
    df['abs_volume_error'] = df['volume_error'].abs()

    stats = df.groupby('category').agg({
        'abs_weight_error': 'mean',
        'abs_volume_error': 'mean',
        'product_version_id': 'count'
    }).rename(columns={'product_version_id': 'count'}).sort_values('abs_volume_error', ascending=False)

    print("\nWorst categories by avg absolute error:")
    print(stats.head(15).to_string())
    stats.to_csv(OUTPUT_DIR / 'category_error_stats.tsv', sep='\t')


def create_visualizations(df: pd.DataFrame):
    print("\n" + "="*60)
    print("CREATING VISUALIZATIONS")
    print("="*60)

    # Setup Korean font
    setup_korean_font()

    # Figure 1: Error distribution overview
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Weight error histogram
    ax1 = axes[0, 0]
    df['weight_error'].clip(-2, 2).hist(bins=50, ax=ax1, color='steelblue', edgecolor='white')
    ax1.axvline(x=0, color='red', linestyle='--')
    ax1.axvline(x=df['weight_error'].median(), color='green', linestyle='--', label=f"Median: {df['weight_error'].median():.2f}")
    ax1.set_title('Weight Error Distribution (clipped ±200%)')
    ax1.set_xlabel('Error')
    ax1.legend()

    # Volume error histogram
    ax2 = axes[0, 1]
    df['volume_error'].clip(-2, 2).hist(bins=50, ax=ax2, color='darkorange', edgecolor='white')
    ax2.axvline(x=0, color='red', linestyle='--')
    ax2.axvline(x=df['volume_error'].median(), color='green', linestyle='--', label=f"Median: {df['volume_error'].median():.2f}")
    ax2.set_title('Volume Error Distribution (clipped ±200%)')
    ax2.set_xlabel('Error')
    ax2.legend()

    # Scatter
    ax3 = axes[1, 0]
    ax3.scatter(df['weight_error'].clip(-2, 2), df['volume_error'].clip(-2, 2), alpha=0.3, s=10)
    ax3.axhline(y=0, color='red', linestyle='--', linewidth=0.5)
    ax3.axvline(x=0, color='red', linestyle='--', linewidth=0.5)
    ax3.set_title('Weight vs Volume Error')
    ax3.set_xlabel('Weight Error')
    ax3.set_ylabel('Volume Error')

    # Pie chart
    ax4 = axes[1, 1]
    if 'volume_error_level' in df.columns:
        counts = df['volume_error_level'].value_counts()
        ax4.pie(counts.values, labels=counts.index, autopct='%1.1f%%')
        ax4.set_title('Volume Error Level')

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'error_distribution.png', dpi=150)
    print(f"Saved: {OUTPUT_DIR / 'error_distribution.png'}")

    # Figure 2: Error by category bar chart
    fig2, axes2 = plt.subplots(1, 2, figsize=(14, 6))

    top_cats = df['category'].value_counts().head(10).index
    df_top = df[df['category'].isin(top_cats)]

    if len(df_top) > 0:
        # Weight error by category
        ax1 = axes2[0]
        df_top.boxplot(column='weight_error', by='category', ax=ax1)
        ax1.set_title('Weight Error by Category (Top 10)')
        ax1.set_xlabel('Category')
        ax1.set_ylabel('Weight Error')
        ax1.set_ylim(-2, 2)
        plt.suptitle('')
        ax1.tick_params(axis='x', rotation=45)

        # Volume error by category
        ax2 = axes2[1]
        df_top.boxplot(column='volume_error', by='category', ax=ax2)
        ax2.set_title('Volume Error by Category (Top 10)')
        ax2.set_xlabel('Category')
        ax2.set_ylabel('Volume Error')
        ax2.set_ylim(-2, 2)
        plt.suptitle('')
        ax2.tick_params(axis='x', rotation=45)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'error_by_category.png', dpi=150)
    print(f"Saved: {OUTPUT_DIR / 'error_by_category.png'}")


def main():
    parser = argparse.ArgumentParser(description='Error Analysis')
    parser.add_argument('--input', '-i', default='colab/20260128_experiment_datasource.tsv')
    parser.add_argument('--no-viz', action='store_true')
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = load_data(args.input)
    analyze_error_overview(df)
    analyze_top_volume_errors(df)
    analyze_top_weight_errors(df)
    analyze_combined_errors(df)
    analyze_dimension_twist(df)
    df = analyze_error_distribution(df)
    analyze_category_stats(df)

    if not args.no_viz:
        create_visualizations(df)

    print(f"\nOutput: {OUTPUT_DIR}")


if __name__ == '__main__':
    main()
