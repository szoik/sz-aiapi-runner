# SZ-AIAPI-Runner

OpenAI API를 사용한 HSCode/무게/부피 추정 테스트 도구입니다.

## 📋 목차

- [개요](#개요)
- [기능](#기능)
- [설치](#설치)
- [환경 설정](#환경-설정)
- [실행](#실행)
- [API 엔드포인트](#api-엔드포인트)
- [사용 예제](#사용-예제)

## 📖 개요

이 프로젝트는 Sazo Korea Shop의 메인 프로젝트에서 OpenAI API 기능을 독립적으로 테스트하기 위한 도구입니다.
상품 정보를 입력하면 OpenAI GPT-4o-mini 모델을 사용하여 다음을 추정합니다:

- **HSCode**: 한국 기준 HS 코드 (10자리 또는 4자리)
- **무게/부피**: 상품의 무게(kg)와 포장 부피(cm)

## ✨ 기능

### 1. HSCode 조회
- 상품명, 카테고리, 이미지 URL을 기반으로 한국 HS 코드 추정
- 신뢰도(probability)와 추정 근거(reason) 제공

### 2. 무게/부피 조회
- 상품의 실제 부피와 포장 부피 추정
- 접을 수 있는 상품(의류, 수건 등)의 경우 압축된 부피 계산
- 무게(kg) 추정

### 3. 통합 조회
- HSCode + 무게/부피를 한 번에 조회 (병렬 처리)

## 🚀 설치

```bash
# 프로젝트 디렉토리로 이동
cd sz-aiapi-runner

# 의존성 설치
npm install
# 또는
yarn install
```

## ⚙️ 환경 설정

### 1. .env 파일 생성

```bash
cp .env.example .env
```

### 2. OpenAI API 키 설정

`.env` 파일을 열고 다음과 같이 설정합니다:

```env
# OpenAI API Key (필수)
OPENAI_API_KEY=sk-proj-your_actual_api_key_here

# 서버 포트 (선택, 기본값: 3100)
SZ_PORT=3100
```

**OpenAI API 키 발급 방법:**
1. https://platform.openai.com/ 접속
2. 로그인 후 API Keys 메뉴로 이동
3. "Create new secret key" 클릭하여 키 생성
4. 생성된 키를 복사하여 `.env` 파일에 붙여넣기

## 🏃 실행

### 개발 모드 (Hot Reload)
```bash
npm run start:dev
# 또는
yarn start:dev
```

### 일반 실행
```bash
npm run start
# 또는
yarn start
```

### 프로덕션 빌드 & 실행
```bash
npm run build
npm run start:prod
# 또는
yarn build
yarn start:prod
```

서버가 정상적으로 시작되면 다음과 같은 메시지가 표시됩니다:

```
========================================
🚀 SZ-OpenAI Tester 서버 시작됨!
📡 서버 주소: http://localhost:3100
📚 Swagger 문서: http://localhost:3100/api-docs
🔑 OpenAI API Key: ✅ 설정됨
========================================
```

## 📡 API 엔드포인트

### 1. 헬스체크
```http
GET /sz-openai-tester/health
```

**응답 예시:**
```json
{
  "status": "ok",
  "service": "SZ-OpenAI-Tester",
  "timestamp": "2025-11-14T08:37:00.000Z"
}
```

### 2. HSCode 조회
```http
POST /sz-openai-tester/hscode
Content-Type: application/json

{
  "productName": "ワイヤレスマウス",
  "category": "Electronics > Computer Accessories",
  "imageUrl": "https://example.com/image.jpg"
}
```

**응답 예시:**
```json
{
  "hscode": "8471601030",
  "hscodeDescription": "Computer mouse is classified under this HS Code...",
  "probability": 0.85,
  "reason": "Based on the product name and category information..."
}
```

### 3. 무게/부피 조회
```http
POST /sz-openai-tester/weight-volume
Content-Type: application/json

{
  "productName": "Large Beach Towel",
  "category": "Home > Towels",
  "imageUrl": "https://example.com/towel.jpg"
}
```

**응답 예시:**
```json
{
  "volume": "20x40x2",
  "packed_volume": "10x20x2",
  "weight": 0.6,
  "reason": "Based on foldability and image analysis."
}
```

### 4. 통합 조회 (HSCode + 무게/부피)
```http
POST /sz-openai-tester/estimate-info
Content-Type: application/json

{
  "productName": "ワイヤレスマウス",
  "category": "Electronics > Computer Accessories",
  "imageUrl": "https://example.com/mouse.jpg"
}
```

**응답 예시:**
```json
{
  "hsCode": {
    "hscode": "8471601030",
    "hscodeDescription": "Computer mouse...",
    "probability": 0.85,
    "reason": "Based on the product name..."
  },
  "estimate": {
    "volume": "12x8x4",
    "packed_volume": "12x8x4",
    "weight": 0.15,
    "reason": "Small electronic device estimation."
  }
}
```

## 📚 사용 예제

### Swagger UI 사용

1. 브라우저에서 http://localhost:3100/api-docs 접속
2. 원하는 엔드포인트 선택
3. "Try it out" 클릭
4. 요청 본문 작성
5. "Execute" 클릭하여 실행

### cURL 사용

```bash
# HSCode 조회
curl -X POST http://localhost:3100/sz-openai-tester/hscode \
  -H "Content-Type: application/json" \
  -d '{
    "productName": "ワイヤレスマウス",
    "category": "Electronics > Computer Accessories",
    "imageUrl": "https://example.com/mouse.jpg"
  }'

# 통합 조회
curl -X POST http://localhost:3100/sz-openai-tester/estimate-info \
  -H "Content-Type: application/json" \
  -d '{
    "productName": "ワイヤレスマウス",
    "category": "Electronics > Computer Accessories",
    "imageUrl": "https://example.com/mouse.jpg"
  }'
```

### Postman 사용

1. Postman 실행
2. 새 요청 생성 (POST)
3. URL: `http://localhost:3100/sz-openai-tester/estimate-info`
4. Headers: `Content-Type: application/json`
5. Body (raw JSON):
   ```json
   {
     "productName": "ワイヤレスマウス",
     "category": "Electronics > Computer Accessories",
     "imageUrl": "https://example.com/mouse.jpg"
   }
   ```
6. Send 클릭

## 🛠️ 기술 스택

- **Framework**: NestJS 10.x
- **Language**: TypeScript 5.x
- **AI API**: OpenAI GPT-4o-mini
- **Documentation**: Swagger/OpenAPI
- **Validation**: class-validator, class-transformer

## 📝 참고사항

- OpenAI API 호출 시 비용이 발생할 수 있습니다.
- GPT-4o-mini 모델을 사용하므로 비용은 상대적으로 저렴합니다.
- 이미지 URL은 선택사항이며, 제공하지 않아도 텍스트 기반으로 추정이 가능합니다.
- temperature는 0.01로 설정되어 있어 결과가 일관적입니다.

## 🤝 기여

이 프로젝트는 Sazo Korea Shop의 내부 테스트 도구입니다.

## 📄 라이선스

UNLICENSED - 사내 전용
