# 데이터 선정
... 을 통해 ##건을 가져온다
총 00 건

# 데이터 정제
* 이미지는 받아서 S3에 올린다
* 데이터의 이미지 URL을 S3로 돌린다

## 빈 값 제외
어떤 빈 값을 제외하는가?
* 제품명?
* 카테고리?
* 이미지?
* 추정치 <- 이건 왜 비는지 모르겠으나 아무튼 빈 거 제외. 400여 건

## 20250109

`uv run python scripts/error_analysis.py inputs/datasource.py`

Input**: `colab/20260128_experiment_datasource.tsv` (default, now should be `inputs/datasource.tsv`)
- **Data**: Top 10 most frequent categories by count
- **Visualization**: Boxplots showing weight_error and volume_error distribution for each of those 10 categories

So it's **10 categories** (the most common ones), not the 2,249 from `category_error_stats.tsv`. The stats file has all categories, but the graph only shows top 10 by frequency.
