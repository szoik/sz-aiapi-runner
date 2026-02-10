| 파일 | 설명 |
|------|------|
| `jsonl_to_tsv.py` | JSONL 원본을 TSV로 변환 |
| `regenerate_derived_datasets.py` | 파생 데이터셋 일괄 재생성 |

`regenerate_derived_datasets.py`

JSONL 원본에서 다음 파생 파일들을 생성:

- `datasource.tsv` - 전체 데이터셋
- `dataset_proper.tsv` - 고유 상품 (동일 상품 구매 건 제거)
  - `datasource_complete.tsv` - **AI 추정값 있는 레코드**. 주요 실험 대상.
  - `datasource_incomplete.tsv` - AI 추정값이나 실측치가 없는 레코드. 일종의 결측치이지만, 왜 이런 문제가 발생했는지 서비스 자체를 분석해야 한다.
- `dataset_duplicated.tsv` - 동일 (중복) 상품. 실측 수치가 일관성이 있는지 등을 파악하는 용도로 사용.
- `missing_estimations.tsv` - 실측값만 있고 AI 추정 없는 레코드
- `categories/*.tsv` - 오차율 등을 기준으로 선별한 카테고리별 파일

## 사용 예시

```bash
# JSONL → TSV 변환
python scripts/etl/jsonl_to_tsv.py

# 파생 데이터셋 재생성
python scripts/etl/regenerate_derived_datasets.py
```

## 데이터 위치

- 원본: `.local/basedata/*.jsonl`
- 출력: `inputs/`
- 백업: `.local/backups/`
