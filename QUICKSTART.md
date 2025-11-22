# 🚀 빠른 시작 가이드

## 1️⃣ 설치

```bash
cd /Users/great/github.com/sazo-korea-shop/sz-aiapi-runner
npm install
```

## 2️⃣ 환경 설정

```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 편집 (OpenAI API 키 입력)
# OPENAI_API_KEY=sk-proj-your_actual_key_here
```

## 3️⃣ 실행

```bash
npm run start:dev
```

서버가 시작되면 자동으로 다음 주소로 접속 가능합니다:
- 서버: http://localhost:3100
- API 문서: http://localhost:3100/api-docs

## 4️⃣ 테스트

### 방법 1: Swagger UI (추천)
1. http://localhost:3100/api-docs 접속
2. `/sz-openai-tester/estimate-info` 엔드포인트 클릭
3. "Try it out" 클릭
4. 다음 예제 데이터 입력:
```json
{
  "productName": "ワイヤレスマウス",
  "category": "Electronics > Computer Accessories",
  "imageUrl": "https://example.com/mouse.jpg"
}
```
5. "Execute" 클릭

### 방법 2: cURL
```bash
curl -X POST http://localhost:3100/sz-openai-tester/estimate-info \
  -H "Content-Type: application/json" \
  -d '{
    "productName": "ワイヤレスマウス",
    "category": "Electronics > Computer Accessories",
    "imageUrl": "https://example.com/mouse.jpg"
  }'
```

### 방법 3: Postman
1. Postman에서 새 POST 요청 생성
2. URL: `http://localhost:3100/sz-openai-tester/estimate-info`
3. Headers에 `Content-Type: application/json` 추가
4. Body → raw → JSON 선택 후 위 예제 데이터 입력
5. Send 클릭

## 📝 주요 엔드포인트

| 엔드포인트 | 설명 |
|-----------|------|
| `GET /sz-openai-tester/health` | 헬스체크 |
| `POST /sz-openai-tester/hscode` | HSCode만 조회 |
| `POST /sz-openai-tester/weight-volume` | 무게/부피만 조회 |
| `POST /sz-openai-tester/estimate-info` | 통합 조회 (권장) |

## ⚠️ 문제 해결

### OpenAI API 키 오류
```
❌ OPENAI_API_KEY 환경변수가 설정되지 않았습니다!
```
→ `.env` 파일에 올바른 OpenAI API 키를 설정했는지 확인하세요.

### 포트 충돌
```
Error: listen EADDRINUSE: address already in use :::3100
```
→ `.env` 파일에서 `SZ_PORT`를 다른 값으로 변경하세요. (예: `SZ_PORT=3200`)

### 의존성 오류
```
npm ERR! code ERESOLVE
```
→ Node.js 버전을 18 이상으로 업그레이드하세요.

## 💡 팁

- 이미지 URL은 선택사항입니다 (없어도 텍스트로 추정 가능)
- 통합 조회(`/estimate-info`)를 사용하면 HSCode와 무게/부피를 한 번에 조회할 수 있습니다
- OpenAI API 호출 시 비용이 발생하므로 필요한 경우에만 사용하세요
