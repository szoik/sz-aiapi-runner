외부 이미지 URL을 로컬/S3로 프록시하여 독립적인 이미지 소스 확보.

# 목적

1. 외부 서비스 블록 방지 - 제3자 서비스에 반복 접근 시 차단 위험 회피
2. 일관된 프롬프트 입력 - 기존 서비스 별 이미지 URL과 같은 접근 수준(http)으로 프롬프트에 입력 처리
  - 편의 상 이미지 이름을 데이터의 키 항목으로 변경하였으며, 이러한 이름 변경이 추정 결과에 영향을 주는지는 확인하지 못했음.

# 스크립트

| 파일 | 설명 |
|------|------|
| `download_images.py` | 외부 URL에서 이미지 다운로드 |
| `upload_images_s3.py` | 로컬 이미지를 S3로 업로드 |
| `split_images.py` | 이미지 폴더를 청크로 분할 (병렬 업로드용) |
| `update_s3_urls.py` | TSV 파일의 thumbnail_url을 S3 URL로 갱신 |

## S3 설정

| 항목 | 값 | 설명 |
|------|-----|------|
| 버킷 | `sazo-qa-ai-resources` | 기본 S3 버킷 |
| 접두어 | `img/` | S3 키 접두어 |
| 최종 URL 형식 | `https://sazo-qa-ai-resources.s3.amazonaws.com/img/{filename}` | 공개 접근 URL |

### 버킷 변경

```bash
# 다른 버킷 사용
python scripts/image_proxy/upload_images_s3.py --bucket my-bucket --prefix images/
```

### AWS 인증

S3 업로드는 boto3를 사용하며, 다음 방법으로 인증:
- 환경 변수: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- AWS 프로필: `~/.aws/credentials`
- IAM 역할 (EC2/Lambda 환경)

## 사용 예시

```bash
# 1. 이미지 다운로드 (1000개씩, 재시작 가능)
python scripts/image_proxy/download_images.py --limit 1000

# 2. 이미지 폴더 분할 (5000개씩, 병렬 업로드용)
python scripts/image_proxy/split_images.py --execute

# 3. S3 업로드
python scripts/image_proxy/upload_images_s3.py --limit 1000
python scripts/image_proxy/upload_images_s3.py --use ix1  # 분할된 폴더

# 4. TSV 파일 URL 갱신
python scripts/image_proxy/update_s3_urls.py
```

## 데이터 위치

| 경로 | 설명 |
|------|------|
| `.local/basedata/images/` | 다운로드된 이미지 |
| `.local/basedata/ix1/`, `ix2/`, ... | 분할된 이미지 폴더 |
| `.local/basedata/image_download_resume.txt` | 다운로드 재시작 지점 |
| `.local/basedata/image_upload_resume.txt` | 업로드 재시작 지점 |
| `.local/basedata/image_download_failed.tsv` | 다운로드 실패 항목 |
| `.local/basedata/image_upload_failed.txt` | 업로드 실패 항목 |

## 워크플로우

```
외부 URL → download_images.py → .local/basedata/images/
                                        ↓
                                split_images.py (선택)
                                        ↓
                                upload_images_s3.py → S3 버킷
                                        ↓
                                update_s3_urls.py → inputs/*.tsv 갱신
```
