# 2026-02-02 작업

## 1. 데이터셋 정리
- (datasource.tsv <- the original)
  - 
- `inputs/dataset_proper.tsv` (8,879건) - 중복/반복 구매 제외한 유니크 상품 데이터셋 생성

#### 2. 오차 분석 스크립트 작성 및 실행
| 스크립트 | 기능 |
|----------|------|
| `error_distribution.py` | 오차 구간별 분포 시각화 |
| `error_top_items.py` | 카테고리별 오차 TOP N 추출 |
| `duplicate_variability.py` | 동일 상품 실측 편차 분석 |
| `category_pattern_analysis.py` | 카테고리별 오차 패턴 분석 |
| `extract_error_samples.py` | 오차 상위 N개 이미지 추출 |

#### 3. 핵심 발견 사항

**과대추정 카테고리 (AI가 너무 크게 추정)**
- 보이그룹 인형/피규어: 41.7%가 +50% 이상 오차
- 방송/예능 인형/피규어: 34.8%
- 원인: 작은 피규어(65~200g)에 300~800g 고정값 적용

**과소추정 카테고리 (AI가 너무 작게 추정)**
- 이어폰팁: 96.0%가 -50% 이하 오차 (20g 고정 추정)
- 볼링가방: 88.7% (볼링공 포함 무게 미인식)
- 화장품(토너/에센스): ~80% (세트 상품을 단품으로 인식)

**문제점**: AI가 특정 값(20g, 30g, 100g, 300g, 800g)에 고정되는 경향

#### 4. 카테고리별 데이터셋 분리
- `inputs/categories/` 폴더에 오차가 큰 TOP 10 카테고리 TSV 파일 생성

#### 5. 프롬프트 v2 작성
- `prompts/weight-volume.v2.system.txt` - 오차 패턴을 반영한 개선 프롬프트

---

# 2026-02-03 작업

## 4단계: 재추정 (v2 프롬프트)

### 전체 데이터셋
- 입력: `inputs/datasource_complete.tsv` (5,585건)
- 출력: `.local/prompt_results/weight-volume.v2.system/datasource_complete/result.tsv`
- 진행: 500건 청크로 실행 중 (3번째 청크 진행 중, 청크당 ~20분)

### 카테고리별 재추정 (10개) ✅ 완료
| 카테고리 | 건수 | 결과 |
|----------|------|------|
| o01_보이그룹_인형피규어 | 168 | ✅ |
| o02_방송예능_인형피규어 | 46 | ✅ |
| o03_바인더 | 23 | ✅ |
| o04_키덜트_피규어인형 | 127 | ✅ |
| o05_토트백 | 46 | ✅ |
| u01_이어폰팁 | 25 | ✅ |
| u02_볼링가방 | 71 | ✅ |
| u03_스킨토너 | 25 | ✅ |
| u04_에센스 | 44 | ✅ |
| u05_시리얼 | 28 | ✅ |

## 5단계: 비교 평가

### 카테고리별 merge 완료 ✅
```bash
# 10개 카테고리 comparison.tsv 생성 완료
.local/prompt_results/weight-volume.v2.system/{카테고리}/comparison.tsv
```

### 번외 작업: 미처리 이미지 다운로드

- 전체 이미지: 4,261개 / 4,537개 (94%)
- 대표 이미지: 1,602개 / 1,766개 (91%)

실패 190건 (헤더 제외), 주요 원인:

| 도메인 | 실패 수 | 비고 |
|--------|---------|------|
| cafe24.poxo.com | 68 | 암호화된 URL, 토큰 만료 |
| cdn.011st.com | 17 | 11번가 CDN |
| gdimg.gmarket.co.kr | 13 | 지마켓 |
| godomall.speedycdn.net | 9 | 고도몰 CDN |
| image.msscdn.net | 6 | 무신사 |

대부분 CDN 접근 제한 또는 토큰 만료로 보입니다.

### 다음 할 일
1. `compare_prompts.py`로 시각화 생성
2. 전체 데이터셋 재추정 완료 후 merge & 비교
