# Input Data Sources

## Dataset Relationships

- **datasource.tsv** (10,185건) - BigQuery 원본, AI 추정값 + 실측값 모두 있음
  - **dataset_proper.tsv** (8,879건) - 유니크 상품 (이미지 URL 기준 중복 제거)
    - **datasource_complete.tsv** (4,610건) - AI 추정값 있음 → 프롬프트 비교 실험용
    - **datasource_incomplete.tsv** (4,269건) - AI 추정값 없음 → 신규 추정 대상
    - **categories/** (10개, 603건) - 오차율 ±50% 기준 카테고리별 서브셋
  - **dataset_duplicated.tsv** (1,306건) - 중복 상품 → 실측값 변동성 분석용

※ `datasource_complete/incomplete.tsv`에는 `dataset_duplicated`에서 온 데이터도 포함 (총 5,585 / ~5,700건)
※ `product_info_details` 필드에 줄바꿈이 있어 `wc -l`과 실제 건수가 다름

### Summary Table

| File | Rows | Description |
|------|------|-------------|
| datasource.tsv | 10,185 | 원본 (AI 추정 + 실측 모두 있음) |
| dataset_proper.tsv | 8,879 | 유니크 상품 (중복 제거) |
| dataset_duplicated.tsv | 1,306 | 중복 상품 (변동성 분석용) |
| datasource_complete.tsv | 5,585 | AI 추정값 있음 (proper 4,610 + dup 일부) |
| datasource_incomplete.tsv | ~5,700 | AI 추정값 없음 (proper 4,269 + dup 일부) |
| missing_estimations.tsv | 414 | 실측 있으나 AI 추정 없음 |
| categories/*.tsv | 603 | 오차 분석용 서브셋 |

---

## datasource.tsv

Main dataset for AI weight/volume estimation experiments.

### How it was made

1. **Source**: BigQuery query from bigquery/dataset.sql
2. **Extraction**: Colab notebook 04_full_dataset_extraction.ipynb
3. **Post-processing**: Column calculations added via Python/Colab

### Source Tables

| Table | Purpose |
|-------|---------|
| sazoshop.firestore_snapshot.v2_order_items | Order item details (product info, AI estimates) |
| sazoshop.firestore_collection.v2_kse_cost | Actual shipping measurements (ground truth) |

### Data Constraints

- Single-item orders only (1 item = 1 package)
- Valid dimensions format: ^\d+\.?\d*x\d+\.?\d*x\d+\.?\d*$
- Weight < 100kg, Volume < 1m3
- Has product title (origin or target)

### Columns (52 total)

#### Identifiers (1-4)
| # | Column | Source |
|---|--------|--------|
| 1 | order_id | v2_order_items.order_item_order_id |
| 2 | item_id | v2_order_items.order_item_id |
| 3 | product_id | v2_order_items.order_item_product_id |
| 4 | product_version_id | v2_order_items.order_item_product_version_id |

#### Input Features - Text (5-14)
| # | Column | Source |
|---|--------|--------|
| 5 | title_origin | order_item_title_origin |
| 6 | title_target | order_item_title_target |
| 7 | category | order_item_product_version_info_category |
| 8 | custom_category | order_item_meta_custom_category_name |
| 9 | site_name | order_item_product_version_site_name |
| 10 | product_details | order_item_product_version_details |
| 11 | product_info_details | order_item_product_version_info_details |
| 12 | materials | order_item_meta_materials |
| 13 | clothing_materials | order_item_meta_clothing_materials |
| 14 | hscode | order_item_meta_hscode |

#### Input Features - Image/Price/URL (15-19)
| # | Column | Source |
|---|--------|--------|
| 15 | thumbnail_urls | order_item_product_version_thumbnail_urls (pipe-separated) |
| 16 | thumbnail_count | ARRAY_LENGTH of above |
| 17 | price_origin | order_item_price_origin_base |
| 18 | price_krw | order_item_price_target_base |
| 19 | product_url | order_item_product_version_url |

#### Ground Truth - Actual Measurements (20-31)
| # | Column | Source | Unit |
|---|--------|--------|------|
| 20 | actual_weight | v2_kse_cost.actual_weight | kg |
| 21 | actual_dimensions | v2_kse_cost.dimensions | WxLxH string |
| 22 | actual_d1 | SPLIT(dimensions, x)[0] | cm |
| 23 | actual_d2 | SPLIT(dimensions, x)[1] | cm |
| 24 | actual_d3 | SPLIT(dimensions, x)[2] | cm |
| 25 | actual_max | GREATEST(d1, d2, d3) | cm |
| 26 | actual_mid | d1 + d2 + d3 - max - min | cm |
| 27 | actual_min | LEAST(d1, d2, d3) | cm |
| 28 | actual_volume_m3 | d1 * d2 * d3 / 1000000 | m3 |
| 29 | actual_volume_cm3 | d1 * d2 * d3 | cm3 |
| 30 | actual_volume_L | d1 * d2 * d3 / 1000 | L |
| 31 | volumetric_weight | v2_kse_cost.volumetric_weight | kg |

#### AI Estimates (32-43)
| # | Column | Source | Unit |
|---|--------|--------|------|
| 32 | ai_weight_kg | order_item_product_version_extra.weight | kg |
| 33 | ai_width_cm | order_item_product_version_extra.width | cm |
| 34 | ai_depth_cm | order_item_product_version_extra.depth | cm |
| 35 | ai_height_cm | order_item_product_version_extra.height | cm |
| 36 | ai_max | GREATEST(width, depth, height) | cm |
| 37 | ai_mid | width + depth + height - max - min | cm |
| 38 | ai_min | LEAST(width, depth, height) | cm |
| 39 | ai_volume_m3 | Derived | m3 |
| 40 | ai_volume_cm3 | Derived | cm3 |
| 41 | ai_volume_L | Derived | L |
| 42 | ai_volume_str | order_item_product_version_extra.volume (string) | - |
| 43 | ai_packed_volume_str | order_item_product_version_extra.packed_volume | - |

#### Error Metrics (44-49) - All Derived
| # | Column | Formula |
|---|--------|---------|
| 44 | weight_error | (ai_weight_kg - actual_weight) / actual_weight |
| 45 | volume_error | (ai_volume_cm3 - actual_volume_cm3) / actual_volume_cm3 |
| 46 | max_error | (ai_max - actual_max) / actual_max |
| 47 | mid_error | (ai_mid - actual_mid) / actual_mid |
| 48 | min_error | (ai_min - actual_min) / actual_min |
| 49 | avg_dim_error | (max_error + mid_error + min_error) / 3 |

#### Metadata (50-52)
| # | Column | Source |
|---|--------|--------|
| 50 | shipping_date | v2_kse_cost.shipping_date |
| 51 | order_created_at | v2_order_items.created_at |
| 52 | weight_range | Categorical bucket of actual_weight |

### Derived Column Formulas

```
ai_volume_cm3 = ai_width_cm * ai_depth_cm * ai_height_cm
ai_volume_m3 = ai_volume_cm3 / 1000000
ai_volume_L = ai_volume_cm3 / 1000

weight_error = (ai_weight_kg - actual_weight) / actual_weight
volume_error = (ai_volume_cm3 - actual_volume_cm3) / actual_volume_cm3
```

Note: Errors are SIGNED (not absolute)
- Positive = AI overestimated
- Negative = AI underestimated

### Statistics

| Metric | Value |
|--------|-------|
| Total rows | 10,185 |
| Columns | 52 |
| Weight error median | -0.41 (underestimates by 41%) |
| Volume error median | -0.90 (underestimates by 90%) |

---

## missing_estimations.tsv

Items that have actual measurements but lack AI estimates.

### How it was made

1. Source: Same BigQuery query as datasource.tsv
2. Filter: Rows where ai_weight_kg, ai_width_cm, ai_depth_cm, ai_height_cm are NULL
3. Extraction: Colab notebook 04_full_dataset_extraction.ipynb + check_missing.py

### Statistics

| Metric | Value |
|--------|-------|
| Total rows | 414 |
| Columns | Same as datasource.tsv |

### Purpose

These items can be used to:
- Run new AI estimations
- Test prompt improvements
- Expand the dataset after estimation
