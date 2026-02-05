#!/bin/bash
cd /Users/great/github.com/sazo-korea-shop/sz-aiapi-runner

# v6 프롬프트 샘플 데이터셋 테스트

# 설정
INPUT_FILE="inputs/datasource_complete_sampling.tsv"
PROMPT_FILE="weight-volume.v6.system.txt"
CHUNK_SIZE=20
WORKERS=10
TITLE="v6 샘플 데이터셋 (n=972)"

# JOB_ID를 실제 생성된 ID로 변경
JOB_ID="20260205-000129"

# 1. 새로운 추정 실행 (split)
#uv run python scripts/split_dataset.py \
#  -i $INPUT_FILE \
#  -p $PROMPT_FILE \
#  --chunk-size $CHUNK_SIZE
# → Job ID 확인 후 위의 JOB_ID 변경

# 2. 병렬 실행
uv run python scripts/run_parallel.py $JOB_ID --workers $WORKERS

# 3. 결과 병합
uv run python scripts/run_parallel.py $JOB_ID --merge

uv run python scripts/merge_results.py \
  -d $INPUT_FILE \
  -r .local/parallel_jobs/$JOB_ID/final_result.tsv \
  -o .local/parallel_jobs/$JOB_ID/comparison.tsv

# 4. 비교 그래프
uv run python scripts/compare_prompts.py \
  -i .local/parallel_jobs/$JOB_ID/comparison.tsv \
  -t "$TITLE"

# 5. 라인 비교 그래프
uv run python scripts/compare_line_chart.py \
  -i .local/parallel_jobs/$JOB_ID/comparison.tsv \
  -t "$TITLE"
