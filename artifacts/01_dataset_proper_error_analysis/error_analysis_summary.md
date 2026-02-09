# AI 무게/부피 추정 오차 분석 종합 리포트

> 작성일: 2026-02-02  
> 데이터셋: `inputs/dataset_proper.tsv` (8,879건, 중복/반복 구매 제외)

---

## 1. 분석 개요

### 1.1 목적
AI 모델의 상품 무게/부피 추정 정확도를 분석하고, 오차가 큰 카테고리의 패턴을 파악하여 프롬프트 개선 방향을 도출한다.

### 1.2 오차 계산 방식
```
오차율 = (AI 추정값 - 실측값) / 실측값
```
- **양수(+)**: 과대추정 (AI가 실제보다 크게 추정)
- **음수(-)**: 과소추정 (AI가 실제보다 작게 추정)

### 1.3 판정 기준
| 구분 | 오차율 범위 |
|------|-------------|
| 정확 | -10% ~ +10% |
| 과대추정 | +50% 이상 |
| 과소추정 | -50% 이하 |

### 1.4 카테고리 추출 기준
**오차건수 비율** (평균 오차율 아님)
- 과대추정: 무게 오차 **+50% 이상**인 건수 / 전체 건수
- 과소추정: 무게 오차 **-50% 이하**인 건수 / 전체 건수
- 최소 20건 이상인 카테고리만 대상

---

## 2. 전체 데이터셋 요약

| 항목 | 값 |
|------|-----|
| 전체 건수 | 8,879건 |
| 데이터 소스 | `inputs/dataset_proper.tsv` |
| 특징 | 중복/반복 구매 제외한 유니크 상품 |

---

## 3. 문제 카테고리 TOP 10

### 3.1 과대추정 TOP 5 (무게 오차 +50% 이상 비율)

| 순위 | 카테고리 | 오차건수/전체 | 비율 |
|------|----------|---------------|------|
| 1 | 보이그룹 인형/피규어 | 70/168 | 41.7% |
| 2 | 방송/예능 인형/피규어 | 16/46 | 34.8% |
| 3 | 바인더 | 7/23 | 30.4% |
| 4 | 키덜트 피규어/인형 | 31/127 | 24.4% |
| 5 | 토트백 | 11/46 | 23.9% |

### 3.2 과소추정 TOP 5 (무게 오차 -50% 이하 비율)

| 순위 | 카테고리 | 오차건수/전체 | 비율 |
|------|----------|---------------|------|
| 1 | 이어폰팁 | 24/25 | 96.0% |
| 2 | 볼링가방 | 63/71 | 88.7% |
| 3 | 스킨/토너 | 20/25 | 80.0% |
| 4 | 에센스 | 35/44 | 79.5% |
| 5 | 시리얼 | 22/28 | 78.6% |

---

## 4. 과대추정 카테고리 상세 분석

### 4.1 보이그룹 인형/피규어 (168건, 41.7%)

**과대추정 TOP 5**
| # | 오차율 | AI | 실측 | URL |
|---|--------|----|----|-----|
| 1 | +566.7% | 800g | 120g | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/9b9308dc-a121-4e0e-8461-b669c942677c.jpg |
| 2 | +361.5% | 300g | 65g | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/0b576010-feeb-4c38-8e90-d69ec4ce9d3d.jpg |
| 3 | +334.8% | 500g | 115g | https://media.bunjang.co.kr/product/310232453_1_1736221124_w{res}.jpg |
| 4 | +252.9% | 300g | 85g | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/c8d814b7-46b1-42ae-a0ab-1addcde5062a.jpg |
| 5 | +252.9% | 300g | 85g | https://media.bunjang.co.kr/product/280913527_{cnt}_1725511963_w{res}.jpg |

**문제점**: 작은 피규어(65~120g)에 300~800g 과대추정

---

### 4.2 방송/예능 인형/피규어 (46건, 34.8%)

**과대추정 TOP 5**
| # | 오차율 | AI | 실측 | URL |
|---|--------|----|----|-----|
| 1 | +200.0% | 300g | 100g | https://media.bunjang.co.kr/product/299284250_{cnt}_1731132130_w{res}.jpg |
| 2 | +140.0% | 300g | 125g | https://media.bunjang.co.kr/product/308746711_1_1735472201_w{res}.jpg |
| 3 | +130.8% | 300g | 130g | https://media.bunjang.co.kr/product/291386354_{cnt}_1727440789_w{res}.jpg |
| 4 | +122.2% | 300g | 135g | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/3907f7f5-bdd1-4359-9d1d-b88c9088b35d.jpg |
| 5 | +106.9% | 300g | 145g | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/321a52de-750f-4d1b-8549-03e5e13e4e51.jpg |

**문제점**: 300g 고정 추정, 실제 100~145g인 작은 인형에 과대추정

---

### 4.3 바인더 (23건, 30.4%)

**과대추정 TOP 5**
| # | 오차율 | AI | 실측 | URL |
|---|--------|----|----|-----|
| 1 | +321.1% | 800g | 190g | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/8a53f2b0-2572-4b94-b7eb-c682937e194a.jpg |
| 2 | +263.6% | 800g | 220g | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/f276cb5c-7948-4cd5-a72a-a0988fe7402f.jpg |
| 3 | +142.4% | 400g | 165g | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/12ba0e8c-2ce8-4fc1-ad3b-2124dc7a19cd.jpg |
| 4 | +105.1% | 400g | 195g | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/8a3b82e9-0d61-4883-8d99-6cea3cd8902a.jpg |
| 5 | +100.0% | 400g | 200g | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/7aeab17c-5aa1-4cb4-ad42-c2c548504b80.jpg |

**문제점**: 빈 바인더(165~220g)에 400~800g 과대추정

---

### 4.4 키덜트 피규어/인형 (127건, 24.4%)

**과대추정 TOP 5**
| # | 오차율 | AI | 실측 | URL |
|---|--------|----|----|-----|
| 1 | +310.3% | 800g | 195g | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/52f64b44-f4ad-4dee-aeee-028d787cc596.jpg |
| 2 | +300.0% | 300g | 75g | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/9cca7255-13dd-40ac-8462-83f53c5bfecb.jpg |
| 3 | +294.7% | 1.5kg | 380g | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/0d34fe94-edc9-40ca-bf3b-e206394486c9.jpg |
| 4 | +275.0% | 300g | 80g | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/3283bf3d-6d29-4a68-b3c8-ef7dac1cec1f.jpg |
| 5 | +275.0% | 300g | 80g | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/23e3f065-c993-4d63-abb7-3fdb08151bbc.jpg |

**문제점**: 소형 피규어(75~195g)에 300~800g 과대추정

---

### 4.5 토트백 (46건, 23.9%)

**과대추정 TOP 5**
| # | 오차율 | AI | 실측 | URL |
|---|--------|----|----|-----|
| 1 | +250.9% | 1.0kg | 285g | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/3e9a152d-54b9-45c8-8c31-42474fa1ae53.jpg |
| 2 | +156.4% | 1.5kg | 585g | https://media.bunjang.co.kr/product/310573986_1_1736388411_w{res}.jpg |
| 3 | +138.8% | 800g | 335g | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/2704cea3-247c-450a-8ee3-188953e4cbb8.jpg |
| 4 | +131.9% | 800g | 345g | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/2e3cdd9c-2c4b-4537-9457-9f3b16782cb0.jpg |
| 5 | +110.5% | 800g | 380g | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/9be4136d-3c4d-49f1-bfeb-5c4cc149d8d7.jpg |

**문제점**: 가벼운 토트백(285~585g)에 800g~1.5kg 과대추정

---

## 5. 과소추정 카테고리 상세 분석

### 5.1 이어폰팁 (25건, 96.0%)

**과소추정 TOP 5**
| # | 오차율 | AI | 실측 | URL |
|---|--------|----|----|-----|
| 1 | -81.8% | 20g | 110g | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/fa201ce8-2823-4341-9a5e-205adb54eb19.jpg |
| 2 | -81.8% | 20g | 110g | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/8c5d97c3-fb41-4297-ad38-37e8d3aa50b9.jpg |
| 3 | -78.9% | 20g | 95g | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/eafb12be-d853-4d27-9ea6-a680f3dbca4c.jpg |
| 4 | -77.8% | 20g | 90g | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/6ff8efe8-7c7d-4efd-a1e9-ba424664ed1b.jpg |
| 5 | -77.8% | 20g | 90g | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/cf3ba491-ce15-4fe5-ab3a-17a831d27e5c.jpg |

**문제점**: 20g 고정 추정, 포장재 포함 실측 90~110g 미반영

---

### 5.2 볼링가방 (71건, 88.7%)

**과소추정 TOP 5**
| # | 오차율 | AI | 실측 | URL |
|---|--------|----|----|-----|
| 1 | -93.0% | 400g | 5.7kg | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/f0bb0673-8b94-400b-8f5a-8064e7aca0b7.png |
| 2 | -83.7% | 1.0kg | 6.1kg | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/60a4d6d8-ee6c-4306-8b9a-ba07ed26066b.jpg |
| 3 | -82.6% | 1.5kg | 8.6kg | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/b9d28b98-14d0-4be1-bec2-a426a3bcb1cb.jpg |
| 4 | -82.1% | 1.5kg | 8.4kg | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/e5afaa21-8988-4629-9541-782935f3ca55.jpg |
| 5 | -81.7% | 1.5kg | 8.2kg | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/aff20ab7-2910-45bd-b0d2-bec412d0ec8e.jpg |

**문제점**: 볼링공 포함 여부 미인식, 가방만으로 400g~1.5kg 추정 (실제 5~8kg)

---

### 5.3 스킨/토너 (25건, 80.0%)

**과소추정 TOP 5**
| # | 오차율 | AI | 실측 | URL |
|---|--------|----|----|-----|
| 1 | -93.8% | 500g | 8.1kg | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/cad917b2-9d6a-4da3-9931-b3876faaeea5.jpg |
| 2 | -93.5% | 500g | 7.8kg | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/0508318f-9372-4524-9b29-122352143293.jpg |
| 3 | -93.3% | 500g | 7.5kg | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/c70af82c-c210-4235-ba59-dbdeb0b34c42.png |
| 4 | -93.3% | 500g | 7.5kg | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/62f490e7-7784-4c26-8bd9-3ed6b08449a5.jpg |
| 5 | -93.2% | 500g | 7.4kg | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/306f4dca-dd06-4fee-8f39-4b056a87306e.jpg |

**문제점**: 대용량/세트 상품(7~8kg)을 단품(500g)으로 추정

---

### 5.4 에센스 (44건, 79.5%)

**과소추정 TOP 5**
| # | 오차율 | AI | 실측 | URL |
|---|--------|----|----|-----|
| 1 | -97.3% | 100g | 3.7kg | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/2e71840b-2e98-40c7-ac3d-8caa8f900aa6.jpg |
| 2 | -93.5% | 100g | 1.6kg | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/19d9c031-a530-4b54-becb-9f19adf7c9fd.jpg |
| 3 | -92.6% | 100g | 1.4kg | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/1844b24a-bc9a-481b-ac53-fa54d84af7a2.jpg |
| 4 | -92.5% | 150g | 2.0kg | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/420c76d6-c2db-40b4-9fb7-5fe1650137b3.jpg |
| 5 | -91.8% | 100g | 1.2kg | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/b31cda91-c479-4313-bba2-8e67da0423fa.jpg |

**문제점**: 대용량/세트 상품(1.2~3.7kg)을 단품(100~150g)으로 추정

---

### 5.5 시리얼 (28건, 78.6%)

**과소추정 TOP 5**
| # | 오차율 | AI | 실측 | URL |
|---|--------|----|----|-----|
| 1 | -98.6% | 30g | 2.2kg | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/f7ba550a-75b6-497f-9761-63d603344403.jpg |
| 2 | -97.5% | 30g | 1.2kg | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/58c19ad8-8016-4cea-bd8d-3e5598975cab.jpg |
| 3 | -97.1% | 30g | 1.0kg | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/7e667c12-3913-498a-b309-feeb0161cdb3.jpg |
| 4 | -96.1% | 30g | 770g | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/8dee78b4-d7ef-4ca9-be1d-c06fb934ddbf.jpg |
| 5 | -91.7% | 800g | 9.7kg | https://sazo-qa-ai-resources.s3.ap-northeast-2.amazonaws.com/img/2b77a567-5936-4434-bf00-c19ca6efeaaf.png |

**문제점**: 30g 고정 추정 (샘플 사이즈?), 실제 대용량 시리얼 1~10kg 미반영

---

## 6. 핵심 발견 사항

### 6.1 AI 고정값 의존 문제
| 카테고리 | AI 고정값 | 실제 범위 |
|----------|-----------|-----------|
| 피규어/인형류 | 300g | 65g ~ 2kg |
| 이어폰팁 | 20g | 55g ~ 110g |
| 시리얼 | 30g | 770g ~ 10kg |
| 볼링가방 | 1.5kg | 5kg ~ 9kg |
| 화장품(토너/에센스) | 100~500g | 1kg ~ 8kg |

### 6.2 공통 오차 패턴

**과대추정 원인**:
- 작은 상품에 일괄 고정값(300g, 800g) 적용
- 재질(플라스틱, 천) 경량성 미반영

**과소추정 원인**:
- 세트/묶음 상품을 단품으로 인식
- 포장재 무게 미반영
- 내용물(볼링공, 화장품 액체) 밀도 미반영

---

## 7. 프롬프트 개선 방향

### 7.1 카테고리별 가이드라인 추가
```
- 피규어/인형: 소형(10cm 이하) 50~150g, 중형 200~500g, 대형 1kg 이상
- 이어폰팁: 포장재 포함 80~150g
- 볼링가방: 볼링공 포함 시 5~8kg, 가방만 1~2kg
- 화장품 세트: 개수 x 단품 무게 + 포장재(500g~1kg)
- 시리얼: 대용량 박스 1~3kg, 묶음 5kg 이상
```

### 7.2 세트/묶음 상품 인식 강화
- "세트", "박스", "대용량", "묶음", "1+1" 키워드 감지
- 이미지에서 다수 상품 포함 여부 확인

### 7.3 고정값 회피 지시
```
특정 값(20g, 30g, 100g, 300g, 800g 등)으로 고정하지 말고,
상품별 특성을 반영하여 추정하세요.
```

---

## 8. 분석 산출물

### 8.1 카테고리 데이터셋
| 파일 | 건수 | 비율 |
|------|------|------|
| `inputs/categories/u01_이어폰팁_err50.tsv` | 25건 | 96.0% |
| `inputs/categories/u02_볼링가방_err50.tsv` | 71건 | 88.7% |
| `inputs/categories/u03_스킨토너_err50.tsv` | 25건 | 80.0% |
| `inputs/categories/u04_에센스_err50.tsv` | 44건 | 79.5% |
| `inputs/categories/u05_시리얼_err50.tsv` | 28건 | 78.6% |
| `inputs/categories/o01_보이그룹_인형피규어_err50.tsv` | 168건 | 41.7% |
| `inputs/categories/o02_방송예능_인형피규어_err50.tsv` | 46건 | 34.8% |
| `inputs/categories/o03_바인더_err50.tsv` | 23건 | 30.4% |
| `inputs/categories/o04_키덜트_피규어인형_err50.tsv` | 127건 | 24.4% |
| `inputs/categories/o05_토트백_err50.tsv` | 46건 | 23.9% |

### 8.2 분석 스크립트
| 스크립트 | 용도 |
|----------|------|
| `scripts/error_distribution.py` | 오차 구간별 분포 그래프 생성 |
| `scripts/error_top_items.py` | 카테고리별 오차 TOP N 항목 추출 |

---

## 9. 다음 단계

1. [ ] 프롬프트 v2 개선 (카테고리별 가이드라인 반영)
2. [ ] 샘플 테스트 실행 (각 카테고리에서 샘플 추출)
3. [ ] 오차 개선 여부 비교 분석
4. [ ] 반복 개선

---

*본 리포트는 `inputs/dataset_proper.tsv` (8,879건) 기준으로 작성되었습니다.*
