# 2026-02-03

## 데이터 파싱 문제 발견

기존 `inputs/datasource.tsv` 파일에 심각한 파싱 문제 발견:
- 총 113,690행 중 정상 파싱 가능: ~5,500행 (52개 컬럼 기준)
- 원인: 필드 내 줄바꿈/탭 문자로 인한 TSV 파싱 오류
- 해결: JSONL 포맷으로 재추출

## Colab 노트북 수정

`colab/04_full_dataset_extraction.ipynb` 수정:
- JSONL 저장 셀 추가 (`df.to_json(..., orient='records', lines=True)`)
- JSONL을 기본 다운로드 포맷으로 변경
- CSV/Parquet은 선택적으로 유지

## 새 데이터 추출

BigQuery에서 JSONL로 재추출:
- 파일: `.local/basedata/single_item_kse_full_20260203.jsonl`
- 크기: 28MB
- 위치: `.local/basedata/` (git 제외)

## 이미지 S3 마이그레이션

`thumbnail_urls`를 S3 URL로 업데이트:
- `dataset_proper.tsv`: 1,602행
- `datasource_complete.tsv`: 933행
- `datasource_incomplete.tsv`: 4,268행
- categories/*.tsv: 89행

## 시각화 스크립트 추가

- `scripts/compare_line_chart.py` - 오차 비교 라인/에어리어 차트
- `scripts/combine_charts.py` - 4개 차트를 1장으로 병합

## 문서 정리

- `WORK.md` 갱신 - JSONL 기반 워크플로우로 재정리
- work log 파일 체계 변경: `work_log_###.md` 형식으로 번호 부여

---

## TSV 파일 재생성 (2026-02-03 오후)

### 문제 확인

기존 TSV 파일들의 멀티라인 문제 재확인:
- `datasource.tsv`: 113,690행 → 실제 10,599 레코드 (파싱 오류)
- 원인: `product_details`, `product_info_details` 등 텍스트 필드 내 줄바꿈/탭 문자

### 해결: JSONL → TSV 변환 스크립트 작성

1. **`scripts/jsonl_to_tsv.py`** - 단순 JSONL→TSV 변환
   - 줄바꿈/탭 문자를 공백으로 치환 (sanitize)
   - 기존 파일 백업 후 덮어쓰기

2. **`scripts/regenerate_derived_datasets.py`** - 모든 파생 파일 재생성
   - `inputs/backups/`에 기존 파일 백업
   - JSONL 소스에서 모든 파생 TSV 재생성

### 재생성된 파일 목록

| 파일 | 레코드 수 | 상태 |
|------|----------|------|
| datasource.tsv | 10,599 | ✓ |
| dataset_proper.tsv | 8,484 | ✓ |
| dataset_duplicated.tsv | 2,115 | ✓ |
| datasource_complete.tsv | 10,185 | ✓ |
| datasource_incomplete.tsv | 414 | ✓ |
| missing_estimations.tsv | 414 | ✓ |
| categories/*.tsv (10개) | 다양 | ✓ |

### 검증 결과

- 모든 파일이 (레코드 수 + 1) 라인으로 정확히 파싱됨
- 52개 컬럼 일관성 유지
- Python csv 모듈로 파싱 테스트 통과

### 이미지 파일 매칭 확인

- `image_download_list.tsv`: 9,440개 (product_version_id 기준)
- JSONL product_version_id: 9,447개
- 공통: 9,440개 ✓
- 이미지 없음: 7개 (원본에 thumbnail_urls가 비어있음)

### 백업 위치

- `inputs/datasource_backup_20260203_161453.tsv` (최초 백업)
- `inputs/backups/` (이후 재생성 시 백업)
