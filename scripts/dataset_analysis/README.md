데이터셋 오류 분포, 특성 분석 도구.

| 파일 | 설명 |
|------|------|
| `error_distribution.py` | 오차 구간별 분포 분석, 시각화 |
| `error_analysis.py` | 오류 통계 분석 |
| `error_top_items.py` | 오차 TOP N 항목 추출 |
| `extract_error_samples.py` | 오류 샘플 추출 |
| `category_pattern_analysis.py` | 카테고리별 패턴 분석 |
| `actual_value_variability.py` | 중복 상품 실측치 변동성 분석 |

# 사용 예시

```bash
# 전체 데이터셋 오류 분포 분석
python scripts/dataset_analysis/error_distribution.py

# 특정 카테고리 분석
python scripts/dataset_analysis/error_distribution.py \
    -i inputs/categories/o01_보이그룹_인형피규어_err50.tsv

# 오차 TOP 10 추출
python scripts/dataset_analysis/error_top_items.py \
    -i inputs/datasource_complete.tsv --top 10
```

# 출력

분석 결과는 `artifacts/dataset_analysis/vw-{serial}-{dataset}/`에 저장합니다.
