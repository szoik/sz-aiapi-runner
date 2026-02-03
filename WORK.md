# Workflow
[1. 데이터 수집] → [2. 오차 분석] → [3. 프롬프트 개선] → [4. 재추정] → [5. 비교 평가] → (반복)

## 변수 정의

| 변수 | 값 | 설명 |
|------|-----|------|
| `${ANALYSIS_DIR}` | `.local/01_dataset_proper_error_analysis` | 현재 분석 결과 디렉토리 |
| `${DATASET}` | `inputs/dataset_proper.tsv` | 분석 대상 데이터셋 (8,879건) |
| `${CATEGORIES_DIR}` | `inputs/categories` | 카테고리별 분리 데이터셋 |

---

# 1단계: 데이터 수집

| 파일  | 설명  | 상태  |
|------|------|------|
| `bigquery/dataset.sql` | 전임자 제공 쿼리 (참고용) | ✅ 완료 |
| `colab/04_full_dataset_extraction.ipynb` | 실제 데이터 추출 노트북 | ✅ 완료 |
| `inputs/datasource.tsv` | 추출된 전체 데이터셋 (**10,185건**) | ✅ 완료 |
| `${DATASET}` | 중복/반복 구매 제외 (**8,879건**) | ✅ 완료 |

* datasource.tsv: 113,690
  * product_info_details 줄바꿈: 4,599 건
* (이미지 기준) 유니크 상품: 8,878건
* 중복 이미지: 1,307 건
  * 2회: 314
  * 3회+: 173
  * 최대: 55

# 2단계: 오차 분석

| 파일 | 설명 | 상태 |
|------|------|------|
| `scripts/error_distribution.py` | 오차 구간별 분포 시각화 | ✅ 완료 |
| `scripts/error_top_items.py` | 카테고리별 오차 TOP N 항목 추출 | ✅ 완료 |
| `scripts/duplicate_variability.py` | 동일 상품 실측 편차 분석 | ✅ 완료 |
| `scripts/category_pattern_analysis.py` | 카테고리별 오차 패턴 분석 | ✅ 완료 |
| `scripts/extract_error_samples.py` | 오차 상위 N개 이미지 추출 | ✅ 완료 |
| `${CATEGORIES_DIR}/*.tsv` | 카테고리별 분리 데이터셋 (10개) | ✅ 완료 |
| `${ANALYSIS_DIR}/error_analysis_summary.md` | 분석 결과 종합 리포트 | ✅ 완료 |

**2단계 산출물**: 어떤 카테고리가, 어떤 방향으로, 얼마나 틀리는지 파악

# 3단계: 프롬프트 개선

| 파일 | 설명 | 상태 |
|------|------|------|
| `prompts/weight-volume.system.txt` | 기존 프롬프트 (OpenAI용) | ✅ 기존 |
| `prompts/weight-volume.v2.system.txt` | 개선 프롬프트 v2 | ✅ 완료 |
| `prompts/weight-volume.v3.system.txt` | 추가 개선 버전 *(필요시)* | 📋 TODO |

**3단계 산출물**: 오차 패턴을 반영한 새 프롬프트

# 4단계: 재추정 (새 프롬프트로 AI 호출)

| 파일 | 설명 | 상태 |
|------|------|------|
| `scripts/weight_volume.py` | OpenAI 추정 스크립트 (기존) | ✅ 기존 |
| `scripts/weight_volume_gemini.py` | Gemini 추정 스크립트 (기존) | ✅ 기존 |
| `scripts/run_estimation.py` | 새 프롬프트로 배치 재추정 *(예정)* | 📋 TODO |
| `dataset/sample_for_test.jsonl` | 테스트용 샘플 (100-200건) *(예정)* | 📋 TODO |
| `${ANALYSIS_DIR}/reestimation/result.jsonl` | 재추정 결과 저장 | 📋 TODO |

**4단계 산출물**: 새 프롬프트로 추정한 결과 데이터

# 5단계: 비교 평가

| 파일 | 설명 | 상태 |
|------|------|------|
| `scripts/compare_results.py` | 기존 vs 신규 추정 비교 *(예정)* | 📋 TODO |
| `${ANALYSIS_DIR}/v1_vs_v2_comparison.md` | 버전별 정확도 비교 리포트 *(예정)* | 📋 TODO |

**5단계 산출물**: 개선 효과 수치화 (오차율 감소폭 등)

---

### 반복 사이클

```
분석 결과 → 프롬프트 수정 → 재추정 → 평가 → (개선될 때까지 반복)
     ↑                                    │
     └────────────────────────────────────┘
```

---

## 현재 위치

```
[1. 데이터 수집] ✅
       ↓
[2. 오차 분석] ✅ 완료
       ↓
[3. 프롬프트 개선] ✅ v2 작성 완료
       ↓
[4. 재추정] ← 여기서 진행 필요
       ↓
[5. 비교 평가]
```

---

## 분석 히스토리

### 2026-02-02: dataset_proper 분석

**데이터셋**: `inputs/dataset_proper.tsv` (8,879건, 중복/반복 구매 제외)

**분석 결과 위치**: `.local/01_dataset_proper_error_analysis/`

**주요 발견**:
1. **과대추정 패턴**: 피규어/인형류에서 300g 고정 추정 → 실제 65~200g인 소형 상품에 과대
2. **과소추정 패턴**: 세트/대용량 상품을 단품으로 인식 (화장품, 시리얼, 볼링가방)
3. **AI 고정값 문제**: 20g, 30g, 100g, 300g, 800g 등 특정 값에 고정되는 경향

**핵심 인사이트**:
- AI 과소추정 심각: 부피 -78%, 치수 -40%
- 카테고리별 편차: 인형/피규어는 과대추정, 화장품/식품은 과소추정
- 실측치 변동성: 같은 상품도 배송마다 2~10배 차이 가능
