프롬프트 버전별 추정 실험, 비교 도구.

# 추정 실행
| 파일 | 설명 |
|------|------|
| `volume_weight_baseline.py` | 기준 버전 추정 (OpenAI) |
| `volume_weight_newprompt.py` | 신규 프롬프트 추정 (OpenAI) |
| `volume_weight_gemini.py` | Gemini 모델 추정 |

# 병렬 처리 파이프라인
| 파일 | 설명 |
|------|------|
| `split_dataset.py` | 데이터셋을 청크로 분할 |
| `run_parallel.py` | 병렬 추정 실행 |
| `merge_results.py` | 청크 결과 병합 |

# 결과 비교
| 파일 | 설명 |
|------|------|
| `compare_prompts.py` | 프롬프트 버전 간 성능 비교 |
| `compare_line_chart.py` | 비교 결과 라인 차트 생성 |

# 파이프라인 사용법

```bash
# 1. 데이터셋 분할
python scripts/prompt_variations/split_dataset.py \
    -i inputs/datasource_complete.tsv \
    -p volume-weight.v003.system.txt

# 2. 병렬 실행
python scripts/prompt_variations/run_parallel.py vw-001-v003-datasource_complete

# 3. 결과 병합
python scripts/prompt_variations/merge_results.py vw-001-v003-datasource_complete

# 4. 비교 분석
python scripts/prompt_variations/compare_prompts.py vw-001-v003-datasource_complete
```

## 출력

실험 결과는 `artifacts/prompt_variations/{job_id}/`에 저장합니다.
