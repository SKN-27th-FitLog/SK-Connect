# Meal ETL Design Analysis (Project Understanding Report)

최근 업데이트된 디자인 문서(개정 초안 v4 및 실패 처리 정책 v1)를 분석한 결과, 시스템의 핵심 약속(Promises)과 데이터 형식(Formats)에 다음과 같은 중요한 변화가 확인되었습니다.

## 1. 운영 및 아키텍처 원칙 (Operating Context)

*   **AWS Lambda 최적화**: 각 Stage(0~5)는 핸들러를 통해 독립적으로 실행 가능해야 하며, 상태 간 전달은 파일(S3/Hive Path)과 명시적 페이로드를 통해서만 이루어집니다.
*   **DB 코드 테이블 중심**: `category_cd`, `status_cd` 등의 상수는 코드 내에 하드코딩하지 않습니다. 반드시 `CodeTableRepository`를 통해 DB에서 실시간 조회해야 합니다. (쿼리 자체는 상수화 가능)
*   **글로벌 변수 사용 금지**: 모듈 수준의 mutable 변수나 싱글톤 세션의 남용을 금지하여 재실행 환경에서의 부작용을 원천 차단합니다.

## 2. 강화된 데이터 포맷 (Data Formats)

### Daily Target (Stage 0)
매일의 수집 대상을 선정하는 단계의 출력 규약이 추가되었습니다.
- `batch_id`: YYYYMMDD_CATEGORY_SEQ 형식
- `selection_policy`: 중복 제외 및 실패 재포함 정책 포함

### Fail Ledger (확장판)
실패 기록 형식이 고도화되었습니다.
- `action`: retry, reprocess, drop 중 하나 (Resolver가 결정)
- `retry_count`: 현재 재시도 횟수 추적
- `entity_completeness`: 메뉴/리뷰 수준의 데이터 완성도(0~1) 기록

### Hive Pathing 표준
모든 파일 저장은 Hive 스타일의 파티션 구조를 따릅니다.
- `crawling=raw/service=shop/year=2026/month=04/day=14/status=fail/`

## 3. 핵심 비즈니스 로직 및 약속 (Critical Promises)

*   **일일 목표 100건 (DB 적재 기준)**: 수집 성공이 아닌, 최종 DB 적재 성공 건수가 100건이 될 때까지 부족분을 보충 수집합니다.
*   **중복 판정 우선순위 (Dedup Hierarchy)**:
    1. `canonical_url`
    2. `normalized_name` + `normalized_address`
    3. `source_platform` + `source_internal_id` (Fallback)
*   **실패 처리 이원화 (Exception vs Reason)**:
    - 시스템 예외(Exception)는 흐름을 중단하고 즉시 로그를 남깁니다.
    - 데이터 품질 이슈(Reason)는 흐름을 유지하되 `Fail Ledger`에 기록하여 후속 처리합니다.
*   **당일 재시도 금지**: 인프라 장애를 제외한 모든 실패 데이터의 재처리는 다음날 배치로 이월하는 것을 원칙으로 합니다.
*   **엔티티별 트랜잭션 분리**: 가게(Store) 적재 실패는 전체 실패지만, 메뉴나 리뷰의 실패는 가게 성공을 유지한 채 별도의 실패 로그로 관리합니다.

## 4. 구조적 변화 (Extract Structure)
문서에서 제시된 `project/app/` (실제 프로젝트에서는 `src/`) 폴더 구조가 이미 반영되어 있으나, `models/` 디렉토리가 비어있는 등 구체적인 데이터 클래스 구현이 다음 단계로 필요합니다.

---
**확인 필요 사항**: 현재 `orchestrator_v4.py`가 존재하지만 구현 내용이 설계서의 "Stage 0~5" 흐름을 모두 준수하는지 상세 검증이 필요합니다.
