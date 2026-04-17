# [SK-Connect] ETL 품질 고도화 실행 계획 (v3.6.1 - 완료)

## 1. 프로젝트 분석 및 현재 상태
- **상태**: **완료 및 검증됨 (2026-04-17)**
- **이슈**: 검증되지 않은 부실 데이터(좌표 0, 주소 공백 등) 및 메뉴 가격 수집 오류 해결.
- **목표**: 100% 무결성 확보 및 대규모 데이터 재적재(Replay) 성공.

---

## 2. 모듈별 최종 설계 (Design Summary)

### 가. 수집 (Extraction) - DiningCodeExtractor (Hybrid King v3.6)
- **추가**: 상세 페이지 정적 HTML(Requests) + 동적 JSON-LD 파싱 연동.
- **수정**: Bot 차단 우회를 위해 Playwright 의존도를 낮추고 데이터 신뢰성 확보.

### 나. 유효성 검증 (Validation) - ShopProcessor
- **검증 게이트**: `validate_master_data()` 메서드 도입.
- **필수 조건**: 주소, 위경도 유효성(!= 0.0), 메뉴 1건 이상 필수. (누락 시 격리)
- **가격 정제**: `safe_int` 정규식 도입으로 '11,000원' 등 문자열 완벽 정수화 (v3.6.1).

### 다. 적재 및 저장 (Loading) - Shop/Review/Post Loader
- **이원화 저장**: `status=success` (적재) / `status=fail` (격리) 분기 완벽 작동.
- **좌표 Fallback**: Kakao API 실패 시 페이지 내부 hidden 필드(`hdn_lat/lng`) 추출 로직 적용.

---

## 3. 세부 구현 태스크 (Tasks) - ALL COMPLETED

- [x] **[Step 1] Kakao API & Constants 보완**
- [x] **[Step 2] 추출기(Extractor) 고도화 (JSON-LD 도입)**
- [x] **[Step 3] 전처리기(Processor) 검증 로직 및 가격 정규식 구현**
- [x] **[Step 4] 로더(Loader) 게이트키퍼 및 Fallback 좌표 구현**
- [x] **[Step 5] 통합 검증 및 데이터 재적재(Replay) 수행**

---

## 4. 최종 수행 결과 (Final Resolution - v3.6.1)

- **데이터 재적재 성공**: 사용자가 지정한 2026-04-17 Raw 파일을 기준으로 재적합 수행.
    - **상점 (Shop)**: 104건 성공 (2건 무결성 부족으로 격리)
    - **리뷰 (Review)**: 678건 성공
    - **메뉴 (Menu)**: 5,366건 성공 (가격 데이터 정수 변환 확인)
- **무결성 확인**: DB 내 `menu.price` 컬럼에 '11,000' 등의 정수값이 정상적으로 안착됨을 확인 (v3.6.1).
- **챗봇 연동**: `crawling` 테이블 적재 완료로 챗봇 추천 무결성 확보.

---

## 5. 운영 규칙 및 제약 사항
- **Rule 5 준수**: 모든 CSV 파일 저장과 DB 적재는 Loader 모듈 내부에서 수행됨.
- **하이브 파티션**: `status=fail` 폴더를 통해 데이터 유효성 위반 원인을 즉시 추적 가능.