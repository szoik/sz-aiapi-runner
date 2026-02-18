# Prompt Version Changelog

## v000 (Baseline)
- 기존 시스템 프롬프트 (pure English)
- Packed volume 개념 도입 (folding, stacking, compression)
- 의류: 3x15x15cm, 0.5kg 표준
- Foldable: 50% 감소, Stackable: 30% 감소

## v002 ~ v007
- 초기 실험 버전들 (세부 기록 없음)

## v008
**착안점**: v7에서 단위 변환 오류 발견 (240g → 240.0kg)
- "WEIGHT MUST BE IN KILOGRAMS (kg)" 명시적 경고 추가
- g→kg 변환 예시 추가: "240g = 0.24kg (NOT 240)"

## v009
**착안점**: 고오차율 항목 분석 결과 bulk 추정 실패 다수 발견
- Image vs Title 가중치 판단 기준 추가
  - Stock photo vs Real photo 구분법
  - 이미지에서 아이템 카운트 지시
- Bulk 추정 가이드라인 추가
  - "랜박", "비공굿", "일괄" 등 키워드 인식
  - Category-specific minimums 테이블
- 이후 pure English로 변환 (한글 예시 제거)

**문제점**: 과대추정 급증 (407건, 43.8%)
- "랜박", "비공굿" 키워드에 과잉 반응 (5-10배 추정)

## v010
**착안점**: v9의 과대추정 문제 해결
- Bulk estimation 지시 전면 제거
- 명시적 정보(무게, 수량) 우선 사용 원칙
- "per unit", "each" 키워드 인식 추가

**결과**: 
- 과대추정 100%+ : 15건 (1.6%) ← 개선
- 그러나 부피 MAE 225.6%로 악화

**문제점**: 부피 과소추정 심각 (90.6%가 과소추정)
- 포토카드를 카드 크기(14cm³)로 추정, 실제는 배송박스(4000cm³)

## v011
**착안점**: 부피 과소추정 해결 + v0의 packed volume 개념 복원
- "Estimate shipping box size, not product size" 강조
- 작은 아이템 최소 배송 크기: 20x15x3cm
- v0의 folding/stacking 규칙 재도입
- 에어매트 등 접어서 배송하는 품목 예시

**문제점**: 과대추정 100%+ 31건으로 증가
- "단품", "개당가격" 무시하고 이미지 수량 카운트
- 포장 무게 과대 추정

## v012
**착안점**: v11의 과대추정 문제 해결 + 명확한 기준 제시
- "shipping box" 강조 제거
- Single Item Keywords 엄격화: "개당", "단품", "낱개" → 1개만
- Weight/Volume Reference Table 추가 (카테고리별 기준값)
- 단위 변환 오류 방지: "62g × 12 = 744g = 0.744kg (NOT 7.44kg)"

**문제점**: 과소추정 급증 (-50% 이하 574건, 61.7%)
- Reference Table이 오히려 제약으로 작용
- 대용량 제품(1000mL, 4L)을 단일 소형 아이템으로 추정
- 명시된 수량 "(1박스100개)" 무시

## v013
**착안점**: v12의 과소추정 문제 해결 + few-shot 구속력 완화
- Reference Table 제거 (고정 기준값이 오히려 방해)
- Priority Order 명시:
  1. Explicit weight in title → use directly
  2. Explicit quantity in title → multiply  
  3. Category + image analysis → estimate
- Liquid Weight Rule 추가: 1mL ≈ 1g (500mL=0.5kg, 1L=1kg, 4L=4kg)
- Few-shot을 "Output Examples"로 변경
  - "format examples only, not constraints"
  - 구체적 제품명 없이 포맷만 제시
- 단위 변환 오류 방지 강화: "NOT 7.44kg", "NOT 240" 명시

## v014
**착안점**: v013 + v010 통합, 과소추정 방지
- v010의 균형 잡힌 구조 기반
- v013의 개선점 통합:
  - Liquid density rule (1mL ≈ 1g)
  - Unit conversion 강조 (÷1000 명시)
- Priority Order 3단계로 정리:
  1. Explicit values (weight, volume, quantity)
  2. Image analysis (count, context)
  3. Category-based reasoning
- Weight Reference Ranges를 "sanity check"로 재정의
  - 제약이 아닌 검증용 참고값
  - "follow the evidence" 명시
- packed_volume = shipping box size 명시 (product와 구분)
- Common calculation mistakes 섹션 추가
- 예시 6개로 다양화 (bulk, liquid, single, figure 등)
