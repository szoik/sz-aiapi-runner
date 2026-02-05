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

- `.local/backups/` (모든 백업 파일)

---

## 병렬 추정 스크립트 구현 (2026-02-03 저녁)

### 배경

`weight_volume_newprompt.py`로 10,185건 처리 시 약 250분 소요 (건당 1.47초).
병렬 처리로 처리 시간 단축 필요.

### 구현한 스크립트

#### 1. `scripts/split_dataset.py` - 데이터셋 분할

입력 TSV를 N개 청크로 분할하여 병렬 처리 준비.

```bash
# 사용법
python scripts/split_dataset.py \
  -i inputs/datasource_complete.tsv \
  -p weight-volume.v2.system.txt

# 출력 구조
.local/parallel_jobs/{job_id}/
├── meta.json           # 작업 메타데이터
├── .chunks_ready       # 분할 완료 마커
└── chunks/
    ├── 0001/input.tsv  # 청크 1 (~100건)
    ├── 0002/input.tsv  # 청크 2
    └── ...
```

**주요 기능:**
- 자동 청크 크기 계산 (기본: ~100건/청크, 약 5분 처리 시간)
- Job ID 자동 생성 (`YYYYMMDD-HHMMSS` 형식)
- 메타데이터 저장 (입력 파일, 프롬프트, 청크 수 등)

#### 2. `scripts/run_parallel.py` - 병렬 실행

분할된 청크를 병렬로 처리.

```bash
# 기본 실행 (5 워커)
python scripts/run_parallel.py {job_id}

# 워커 수 지정
python scripts/run_parallel.py {job_id} --workers 8

# 상태 확인
python scripts/run_parallel.py {job_id} --status

# 결과 병합
python scripts/run_parallel.py {job_id} --merge
```

**주요 기능:**
- `ProcessPoolExecutor`로 병렬 처리
- `rich` 라이브러리로 인터랙티브 진행률 표시
  - 각 워커 상태 실시간 표시 (처리 중 청크, 경과 시간)
  - 전체 진행률 바
  - 완료/실패 청크 목록
- `.done` 마커로 청크별 완료 추적 (중단 후 재개 가능)
- 결과 파일 자동 병합

**출력 예시:**
```
Job: 20260203-182520
Prompt: weight-volume.v2.system.txt
Total chunks: 102
Completed: 45
Pending: 57
Workers: 5
------------------------------------------------------------
Worker      Status        Chunk     Elapsed
[Worker 1]  processing    0046      45.2s
[Worker 2]  processing    0047      32.1s
[Worker 3]  processing    0048      28.7s
[Worker 4]  processing    0049      41.3s
[Worker 5]  processing    0050      15.4s

Overall: ████████████████░░░░░░░░░░░░░░░░░░░░░░░░  44% • 0:22:34 < 0:28:26

... ✓0035 ✓0036 ✓0037 ✓0039 ✓0040 ✓0041 ✓0043 ✓0044 ✓0045
```

### 전체 워크플로우

```bash
# 1. 데이터셋 분할
python scripts/split_dataset.py -i inputs/datasource_complete.tsv -p weight-volume.v2.system.txt
# → Job ID 출력: 20260203-182520

# 2. 병렬 실행
python scripts/run_parallel.py 20260203-182520 --workers 5

# 3. 결과 병합
python scripts/run_parallel.py 20260203-182520 --merge
# → .local/parallel_jobs/20260203-182520/final_result.tsv
```

### 예상 성능

| 워커 수 | 예상 시간 | Rate Limit 사용 |
|--------|----------|----------------|
| 1 (순차) | ~250분 | ~50 RPM |
| 4 | ~62분 | ~200 RPM |
| 5 | ~50분 | ~250 RPM |
| 8 | ~31분 | ~400 RPM |

OpenAI API rate limit: 3,500 RPM (여유 있음)

### 의존성 추가

- `rich` 라이브러리 추가 (`uv add rich`)

### Git 브랜치

- `feat/parallel-estimation` 브랜치에서 작업
- 커밋:
  - `feat: add parallel estimation scripts (split_dataset, run_parallel)`
  - `feat: add tqdm progress bar to parallel execution`
  - `feat: add rich interactive worker display for parallel execution`

---

## 병렬 실행 스크립트 버그 수정 (2026-02-03 저녁 ~22:00)

### 발생한 문제들

`run_parallel.py`의 인터랙티브 진행률 표시가 제대로 동작하지 않음:
1. 개별 청크의 progress bar가 항상 0%로 표시
2. resume 시 이미 완료된 청크들이 Overall progress에 반영 안 됨

### 원인 및 해결

#### 1. subprocess 환경 문제 (uv + ProcessPoolExecutor + subprocess 조합)

**문제**: `ProcessPoolExecutor`에서 subprocess로 `weight_volume_newprompt.py` 실행 시, 프로젝트 가상환경(`.venv`)의 패키지를 찾지 못함.

**배경 - 실행 환경 체인**:
```
uv run python run_parallel.py
  └─ ProcessPoolExecutor (fork)
       └─ subprocess.run(weight_volume_newprompt.py)
```

일반적으로 `uv run python`으로 실행하면 uv가 `.venv`를 활성화하고 올바른 Python을 사용합니다. 그런데 문제는 **ProcessPoolExecutor + subprocess.run 조합**에서 발생:

1. **`uv run python`**: uv가 `.venv` 활성화 → 정상 작동
2. **ProcessPoolExecutor fork**: 부모 프로세스의 환경 상속 → 여기까진 괜찮음
3. **subprocess.run**: 새 프로세스 생성 시 Python 인터프리터 선택이 문제

**원인 분석**:

처음에는 `sys.executable`을 사용했는데, 이게 예상과 다르게 동작:
```python
# uv run 환경에서
>>> import sys
>>> sys.executable
'/Users/great/github.com/sazo-korea-shop/sz-aiapi-runner/.venv/bin/python3'

# 그런데 이 python3은 심볼릭 링크:
# .venv/bin/python -> /opt/homebrew/opt/python@3.14/bin/python3.14
```

`.venv/bin/python`은 시스템 Python으로의 심볼릭 링크입니다. 이 Python을 직접 실행하면 **venv의 site-packages를 자동으로 인식하지 못함** - `VIRTUAL_ENV` 환경변수가 있어야 venv가 활성화됩니다.

`uv run`은 이 환경변수들을 자동 설정하지만, subprocess.run으로 새 프로세스를 만들 때는 명시적으로 전달해야 합니다.

**해결**: 
- `.venv/bin/python`을 직접 사용
- 환경변수 `VIRTUAL_ENV`, `PATH` 명시적 설정
- `PYTHONUNBUFFERED=1` 추가로 출력 버퍼링 방지

```python
venv_dir = project_root / ".venv"
venv_python = venv_dir / "bin" / "python"

env = os.environ.copy()
env["VIRTUAL_ENV"] = str(venv_dir)
env["PATH"] = f"{venv_dir}/bin:{env.get('PATH', '')}"
env["PYTHONUNBUFFERED"] = "1"

subprocess.run([str(venv_python), ...], env=env, ...)
```

**왜 `uv run python`을 subprocess에서 쓰면 안 되나?**

시도해봤지만 실패:
```python
subprocess.run(["uv", "run", "python", script_path, ...])
```

이 경우 uv가 다시 환경을 설정하면서 예상치 못한 Python을 선택하는 경우가 있었음. 특히 ProcessPoolExecutor 내부에서 실행될 때 cwd나 환경이 달라지면서 uv가 다른 Python을 찾는 문제 발생.

#### 2. stdout 파이프 버퍼링 문제

**문제**: `capture_output=True`로 subprocess 실행 시, stdout이 파이프가 되어 full buffering 발생. 파이프 버퍼가 가득 차면 프로세스가 블로킹됨.

**해결**: stdout을 파일(`run.log`)로 리다이렉트

```python
log_file = chunk_dir / "run.log"
with open(log_file, "w", encoding="utf-8") as log_f:
    result = subprocess.run(
        [...],
        stdout=log_f,
        stderr=subprocess.STDOUT,
        ...
    )
```

#### 3. 상대경로 문제

**문제**: `ProcessPoolExecutor`에서 fork된 프로세스의 작업 디렉토리가 달라질 수 있어 상대경로가 동작하지 않음.

**해결**: `get_project_root()`와 `chunk_dir`에 `.resolve()` 추가하여 절대경로 사용

```python
def get_project_root() -> Path:
    return Path(__file__).parent.parent.resolve()

def run_chunk(chunk_dir: Path, prompt_file: str):
    chunk_dir = chunk_dir.resolve()
    ...
```

#### 4. progress.json이 쓰이지 않음

**문제**: `weight_volume_newprompt.py`의 `write_progress()` 함수에서 `json.dump()` 호출 시 `NameError: name 'json' is not defined` 발생. 예외가 `except Exception: pass`로 무시됨.

**원인**: `import json`이 누락됨.

**해결**: 
- `import json` 추가
- 예외 발생 시 stderr로 에러 메시지 출력하도록 변경

```python
# scripts/weight_volume_newprompt.py
import json  # 추가

def write_progress(...):
    try:
        ...
        with open(progress_file, "w", encoding="utf-8") as f:
            json.dump(progress_data, f)
            f.flush()
    except Exception as e:
        print(f"[PROGRESS ERROR] {e}", file=sys.stderr)
```

#### 5. resume 시 초기 상태 반영 안 됨

**문제**: 스크립트 재시작 시 이미 완료된 청크들이 `completed_chunks` 목록과 Overall progress에 반영되지 않음.

**해결**: 시작 시 이미 완료된 청크들을 초기값으로 설정

```python
completed_chunks: list[str] = [c.name for c in completed]  # 이미 완료된 청크들
success_count = len(completed)

overall_task_id = overall_progress.add_task(
    "overall", 
    total=len(completed) + len(pending),
    completed=len(completed)  # 시작점 설정
)
```

### 최종 결과

- 개별 청크 progress bar 실시간 업데이트 ✓
- resume 시 완료된 청크 반영 ✓
- 안정적인 병렬 실행 ✓

### 수정된 파일

- `scripts/run_parallel.py`
  - `import os` 추가
  - subprocess 환경변수 설정
  - stdout을 파일로 리다이렉트
  - 경로 `.resolve()` 추가
  - resume 초기 상태 설정
  
- `scripts/weight_volume_newprompt.py`
  - `import json` 추가
  - `write_progress()` 예외 처리 개선

---

## 청크 중단 후 재개 기능 개선 (2026-02-03 ~23:30)

### 문제

청크 처리 중 강제 중단(Ctrl+C) 후 다시 실행하면, 해당 청크를 처음부터 다시 처리함. 이미 처리한 항목들이 낭비됨.

### 원인 분석

1. **파일 버퍼링**: `writerow()` 후 `flush()`를 하지 않아 강제 중단 시 버퍼 데이터 손실
2. **손상된 TSV 처리**: 중단 시 불완전하게 기록된 마지막 줄이 파싱 오류 유발 가능
3. **progress 표시**: resume 시 이미 처리된 항목 수가 progress bar에 반영 안 됨

### 해결

#### 1. 매 행 쓰기 후 flush 추가

```python
writer.writerow({...})
out_f.flush()  # 즉시 디스크에 기록
```

#### 2. 손상된 TSV 파일 처리 개선

`get_processed_order_ids()` 함수 재작성:
- `csv.DictReader` 대신 직접 라인 파싱
- 헤더 컬럼 수와 다른 필드 수를 가진 줄은 건너뜀 (불완전한 줄)
- 파일 읽기 오류 시 안전하게 빈 set 반환

```python
expected_field_count = len(fieldnames)

for line_num, line in enumerate(lines[1:], start=2):
    fields = line.split("\t")
    
    # 불완전한 줄 건너뛰기
    if len(fields) < expected_field_count:
        print(f"Warning: Skipping incomplete line {line_num}", file=sys.stderr)
        continue
    
    order_id = fields[order_id_idx]
    if order_id:
        order_ids.add(order_id)
```

#### 3. resume 시 progress 표시 수정

이미 처리된 항목 수를 초기값으로 반영:

```python
already_processed = len(processed_ids) if resume else 0
write_progress(already_processed, total_records, "starting")

processed = already_processed  # 0이 아닌 이미 처리된 수부터 시작
```

### UI 정리

- 헤더에서 중복 정보 제거 (Completed/Pending - 하단과 중복)
- 하단 status line에서 Total 제거 (고정값이라 불필요)
- 헤더에 chunk size 표시 추가

### 수정된 파일

- `scripts/weight_volume_newprompt.py`
  - `out_f.flush()` 추가
  - `get_processed_order_ids()` 재작성
  - resume 시 progress 초기값 설정

- `scripts/run_parallel.py`
  - 헤더에서 Completed/Pending 제거
  - status line에서 Total 제거
  - chunk size 표시 추가

---

## TODO

### UI 정리
- 청크 사이즈 같은 항목을 같은 차원에 두기
- 처리할 총 개수 표시

### 스크립트 연결
- 3개 스크립트 (split_dataset, run_parallel, merge) 자동 연결 실행
- 개별 실행도 가능하게 유지

### 진행 상황 표시 개선
- 개별 청크에서 실패 항목 표시 (세로 빨간 줄?)
- 현재 처리중인 항목명 프로그레스 바 옆에 표시
