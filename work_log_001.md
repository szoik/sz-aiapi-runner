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
