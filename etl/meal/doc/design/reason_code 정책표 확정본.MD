==================================================
[reason_code 정책표 확정본 v2 - DB 구조 반영]
==================================================

1. 목적

reason_code 정책표는 각 stage 및 DB 적재 과정에서 발생하는 실패 및 경고 상황을
표준 코드로 정의하고, 각 코드별 후속 action을 일관되게 결정하기 위한 기준이다.

본 정책표는 다음을 보장한다.

- 동일 현상 → 동일 reason_code 및 동일 action 적용
- status가 아닌 reason_code 기반 의사결정
- 무한 retry 방지
- 서비스 연속성 유지
- 데이터 손실 최소화
- 운영자 개입 지점 명확화


==================================================
2. 공통 운영 정책
==================================================

1) 같은 날 재시도 금지
- 모든 retry는 다음날 배치로 이월한다.

2) retry 최대 횟수
- 최대 retry_count = 5
- retry_count >= 5 → retry 중단

3) retry 이후 처리
- maps: retry → reprocess 또는 운영 검토
- shop: reprocess → success_with_warning 전환
- 기타: 정책별 처리

4) 판단 기준
- status가 아닌 reason_code 기준으로 action 결정

5) warning 처리
- status = success_with_warning
- 데이터 적재는 성공으로 간주하되 품질 이슈 기록

6) fail ledger 필수 필드
- stage
- reason_code
- action
- retry_count
- entity_type
- entity_id
- failed_at


==================================================
3. action 정의
==================================================

retry
- 동일 로직으로 다음날 재시도

reprocess
- 파서/정규화/데이터 수정 후 재처리

drop
- 재시도 및 재처리 대상에서 제외

load_with_warning
- 적재는 진행, warning 기록

alert_only
- 적재 실패와 무관, 운영 알림/로그만 기록


==================================================
4. Load 단계 엔티티 중요도 정책
==================================================

maps
- 핵심 엔티티 (필수)
- 실패 시 전체 실패
- action: retry

shop
- 준핵심 엔티티
- 실패 시 reprocess
- 3회 이상 실패 시 success_with_warning 또는 운영 검토

menu
- 부가 엔티티
- 실패 시 load_with_warning

crawling
- 비핵심 엔티티
- 실패 시 alert_only


==================================================
5. Stage별 reason_code 정책표
==================================================

--------------------------------------------------
[Stage 1. Raw Collection]
--------------------------------------------------

NETWORK_ERROR
- action: retry

TIMEOUT
- action: retry

TEMPORARY_RENDER_FAIL
- action: retry

RATE_LIMITED
- action: retry

INVALID_URL
- action: drop

BLOCKED_SOURCE_POLICY
- action: drop


--------------------------------------------------
[Stage 2. Candidate Parsing]
--------------------------------------------------

SELECTOR_MISMATCH
- action: reprocess

EMPTY_EXTRACTION
- action: reprocess

NOT_RESTAURANT_ENTITY
- action: drop


--------------------------------------------------
[Stage 3. Validation & Normalization]
--------------------------------------------------

AMBIGUOUS_MENU_NAME
- action: load_with_warning

UNDEFINED_CODE_DETECTED
- action: load_with_warning

MISSING_NORMALIZED_NAME
- action: reprocess

MISSING_NORMALIZED_ADDRESS
- action: reprocess

PERMANENT_SCHEMA_VIOLATION
- action: drop


--------------------------------------------------
[Stage 3. Dedup]
--------------------------------------------------

DEDUP_KEY_NOT_GENERATABLE
- action: reprocess

CONFLICTING_DEDUP_SIGNALS
- action: reprocess
- severity: high

INVALID_CANONICAL_URL
- action: fallback
- fail 아님


--------------------------------------------------
[Stage 4. Load - DB 기준]
--------------------------------------------------

MAP_INSERT_FAILED
- entity: maps
- action: retry
- retry_count >= 5 → reprocess 또는 운영 검토

MAP_DUPLICATE_DETECTED
- entity: maps
- action: drop

SHOP_INSERT_FAILED
- entity: shop
- action: reprocess
- retry_count >= 3 → success_with_warning 또는 운영 검토

MENU_INSERT_FAILED
- entity: menu
- action: load_with_warning

CRAWLING_INSERT_FAILED
- entity: crawling
- action: alert_only


--------------------------------------------------
[Stage 5. Fail Classification]
--------------------------------------------------

RETRY_LIMIT_EXCEEDED
- action: drop

UNKNOWN_REASON_CODE
- action: alert_only


==================================================
6. 핵심 판단 원칙
==================================================

1) maps 기준 원칙
- maps가 없으면 시스템 성립 불가
- 반드시 성공해야 하는 엔티티

2) 부분 실패 허용 원칙
- shop/menu/crawling은 부분 실패 허용
- 단, shop은 재처리 대상 유지

3) retry vs reprocess

retry:
- 환경 문제 (네트워크, DB 등)

reprocess:
- 데이터 문제 (파싱, dedup, validation)

4) dedup 처리

DEDUP_KEY_NOT_GENERATABLE → reprocess
CONFLICTING_DEDUP_SIGNALS → reprocess
canonical_url 문제 → fallback

절대 drop 금지


5) UNKNOWN 코드 처리

- 적재 유지
- action = load_with_warning
- 운영 알림 대상


==================================================
7. 운영 주의사항
==================================================

- reason_code는 Enum 형태로 관리
- 새로운 reason_code 추가 시 반드시 action 정의 필요
- fail ledger는 운영 데이터이며 logger와 분리
- 동일 reason_code는 전체 시스템에서 동일 의미 유지

[reason_code 정책 정의 변경]

* reason_code → action 매핑은 정책 테이블이 아니라 resolver에서 결정한다.
* Exception class는 reason_code만 정의한다.
* action, severity, retry 정책은 resolver에서 관리한다.
