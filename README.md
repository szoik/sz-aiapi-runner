# AI 무게/부피 추정 개선 프로젝트

## Objective

기존에 LLM을 활용하여 쇼핑몰에서 제품의
- (사용자가 등록한) 상품 제목
- (쇼핑몰의 분류체계에 따라 지정한) 상품 카테고리
- (사용자가 등록한) 상품 사진

정보를 통해 상품의 부피/무게를 추정.
상품의 부피,무게와 포장 부피,무게를 같이 추정함.

이후 실제 배송사에서 상품 발송 시 적용한 부피, 무게 값이 있는데 이 값과 앞서 추정한 값이 차이가 없도록 해야 함.

데이터베이스에서 추정치와 실측치를 가져와서 이 값을 어떻게 분류하여 개선 프롬프트를 적용할 지 전략을 세워야 한다.

**오차 = |실측치 - 추정치| / 실측치**

기본적으로 구성하는 전략은 이 오차의 분포를 살펴보고, 개선 가능성과 효과가 높으리라 예상하는 일정 수준 이상의 오차, 예를 들어 0.5 이상인 대상들부터 선정하여 진행.

오차가 큰 대상들이 어떤 패턴을 갖추고 있는 경우(예: 오차가 큰 대부분이 가구류), 특정 제품군부터 개선하는 전략으로 진행.

---

## 워크플로우

```
[1. 데이터 수집] → [2. 데이터 전처리] → [ 3. 오차 분석  ]
      ↑             (반복)              ↓
[ 6. 비교 평가 ] ← [  5. 재추정   ] ← [4. 프롬프트 개선]
```

---

## 1단계: 데이터 수집 (BigQuery → Colab → JSONL)

BigQuery에서 단일 상품 주문 + KSE 실측 데이터를 추출.

### 1.1 Colab 노트북 실행

```
colab/04_full_dataset_extraction.ipynb    # BigQuery에서 데이터 추출
```

**실행 절차:**
1. Google Colab에서 노트북 열기
2. BigQuery 인증 (`auth.authenticate_user()`)
3. 전체 셀 실행
4. **JSONL 파일 다운로드** (권장 포맷)

### 1.2 다운로드 파일 배치

```bash
# 다운로드된 파일을 gdrive/basedata/로 이동
mv ~/Downloads/single_item_kse_full_YYYYMMDD.jsonl gdrive/basedata/
```

**산출물:** `gdrive/basedata/single_item_kse_full_YYYYMMDD.jsonl`

> **주의:** JSONL 포맷 사용 권장. TSV/CSV는 필드 내 줄바꿈/탭으로 파싱 오류 발생 가능.

---

## 2단계: 데이터 전처리

JSONL에서 분석용 데이터셋을 생성합니다.

### 2.1 데이터셋 분리

```bash
# JSONL → TSV 변환 및 분리
uv run python scripts/prepare_dataset.py \
    -i gdrive/basedata/single_item_kse_full_YYYYMMDD.jsonl \
    -o inputs/
```

**산출물:**

| 파일 | 설명 |
|------|------|
| `inputs/datasource.tsv` | 전체 데이터 |
| `inputs/dataset_proper.tsv` | 유니크 상품 (중복 제외) |
| `inputs/dataset_duplicated.tsv` | 중복 구매 상품 |
| `inputs/datasource_complete.tsv` | AI 추정값 있는 상품 |
| `inputs/datasource_incomplete.tsv` | AI 추정값 없는 상품 |

### 2.2 데이터셋 관계

```
datasource.tsv (전체)
├── dataset_proper.tsv (유니크 상품)
│   ├── datasource_complete.tsv (AI 추정 있음)
│   └── datasource_incomplete.tsv (AI 추정 없음)
└── dataset_duplicated.tsv (중복 구매)
```

---

## 3단계: 오차 분석

기존 AI 추정값과 실측값의 오차를 분석합니다.

### 3.1 분석 스크립트

| 스크립트 | 기능 |
|----------|------|
| `scripts/error_distribution.py` | 오차 구간별 분포 시각화 |
| `scripts/error_top_items.py` | 카테고리별 오차 TOP N 추출 |
| `scripts/category_pattern_analysis.py` | 카테고리별 오차 패턴 분석 |
| `scripts/extract_error_samples.py` | 오차 상위 N개 이미지 추출 |

### 3.2 실행 예시

```bash
# 오차 분포 분석
uv run python scripts/error_distribution.py -i inputs/datasource_complete.tsv

# 카테고리별 오차 TOP 50 추출
uv run python scripts/error_top_items.py -i inputs/datasource_complete.tsv -n 50 -o inputs/categories/
```

**산출물:**
- `inputs/categories/*.tsv` - 카테고리별 오차 상위 데이터
- `artifacts/error_analysis/` - 분석 결과 리포트 및 시각화

---

## 4단계: 프롬프트 개선

오차 분석 결과를 바탕으로 프롬프트를 개선합니다.

| 파일 | 설명 |
|------|------|
| `prompts/weight-volume.v0.system.txt` | 초기 프롬프트 |
| `prompts/weight-volume.v2.system.txt` | 개선 프롬프트 v2 |
| `prompts/weight-volume.v3.system.txt` | 개선 프롬프트 v3 |
| ... | |
| `prompts/weight-volume.v7.system.txt` | 개선 프롬프트 v7 |

**개선 방향:**
- 과대추정 카테고리: 더 보수적인 추정 유도
- 과소추정 카테고리: 세트/대용량 인식 강화
- 고정값 문제: 다양한 값 출력 유도

---

## 5단계: 재추정 (새 프롬프트로 AI 호출)

### 5.1 추정 스크립트

| 스크립트 | 설명 |
|----------|------|
| `scripts/weight_volume.py` | OpenAI 추정 (기본) |
| `scripts/weight_volume_gemini.py` | Gemini 추정 |
| `scripts/weight_volume_newprompt.py` | 새 프롬프트로 배치 재추정 (resume 지원) |
| `scripts/run_parallel.py` | 병렬 추정 실행 |

### 5.2 실행 예시

```bash
# 전체 실행 (500건씩, resume 가능)
uv run python scripts/weight_volume_newprompt.py \
    -i inputs/datasource_complete.tsv \
    -p weight-volume.v2.system.txt \
    -o artifacts/prompt_results/v2/datasource_complete/result.tsv \
    -l 500 \
    --resume
```

**산출물:** `artifacts/prompt_results/{버전}/{데이터셋}/result.tsv`

---

## 6단계: 비교 평가

새 프롬프트 결과와 기존 결과를 비교합니다.

### 6.1 결과 병합

```bash
uv run python scripts/merge_results.py \
    -d inputs/datasource_complete.tsv \
    -r artifacts/prompt_results/v2/datasource_complete/result.tsv
```

**산출물:** `comparison.tsv` (기존 추정 + 신규 추정 + 실측값)

### 6.2 시각화

```bash
uv run python scripts/compare_prompts.py \
    -i artifacts/prompt_results/v2/datasource_complete/comparison.tsv
```

**산출물:**
- `chart_comparison.png` - 히스토그램 비교
- `chart_scatter.png` - 산점도 비교
- `chart_line.png` - 라인 차트 비교
- `stats.md` - 통계 요약

### 6.3 추가 시각화 스크립트

| 스크립트 | 기능 |
|----------|------|
| `scripts/compare_line_chart.py` | 오차 비교 라인/에어리어 차트 |
| `scripts/combine_charts.py` | 4개 차트를 1장으로 병합 |

---

## 반복 사이클

```
오차 분석 → 프롬프트 수정 → 재추정 → 평가 → (개선될 때까지 반복)
     ↑                                    │
     └────────────────────────────────────┘
```

---

## 디렉토리 구조

```
sz-aiapi-runner/
├── scripts/                        # Python 스크립트
│   ├── weight_volume.py            # 기본 추정
│   ├── weight_volume_newprompt.py  # 새 프롬프트 재추정
│   ├── run_parallel.py             # 병렬 실행
│   ├── merge_results.py            # 결과 병합
│   ├── compare_prompts.py          # 비교 시각화
│   ├── error_*.py                  # 오차 분석
│   └── ...
├── inputs/                         # 입력 데이터
│   ├── datasource*.tsv             # 데이터셋
│   ├── dataset_*.tsv               # 가공된 데이터셋
│   └── categories/                 # 카테고리별 데이터
├── prompts/                        # 프롬프트 파일
│   ├── weight-volume.v0.system.txt # 초기 버전
│   ├── weight-volume.v2.system.txt
│   └── ...v7.system.txt
├── artifacts/                      # 실험 결과물
│   ├── prompt_results/             # 프롬프트별 추정 결과
│   ├── error_analysis/             # 오차 분석 결과
│   └── category_analysis/          # 카테고리 분석
├── colab/                          # Colab 노트북
│   └── 04_full_dataset_extraction.ipynb
├── bigquery/                       # BigQuery 쿼리
│   ├── dataset.sql
│   └── experiment_samples.sql
├── gdrive -> ...                   # Google Drive 링크
│   └── basedata/                   # 원본 JSONL
└── .local/                         # 로컬 임시 파일 (git 제외)
```
