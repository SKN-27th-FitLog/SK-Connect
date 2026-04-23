==================================================
[jsonl 기반 크롤링 파이프라인 폴더 구조 + 클래스 설계 확정본 v1]
==================================================

0. 문서 목적

본 문서는 DB 테이블 설계를 먼저 진행하지 않고,
JSONL 저장 방식을 전제로 한 크롤링 파이프라인의
폴더 구조와 클래스 설계를 확정하기 위한 문서이다.

본 문서는 구현 코드가 아니라 구조 설계만 다룬다.

핵심 원칙:
- 저장은 DB가 아니라 JSONL 중심으로 진행한다.
- 정책은 코드에 하드코딩하지 않고 resolver 구조로 분리한다.
- stage는 정책 판단을 하지 않는다.
- exception / resolver / fail ledger / stage I/O 책임을 분리한다.


==================================================
1. 최상위 구조
==================================================

project/
  app/
    handlers/
    pipeline/
    exceptions/
    policies/
    enums/
    models/
    stages/
    resolvers/
    storage/
    logging/
    utils/
    config/

  data/
    raw/
    candidate/
    normalized/
    fail_ledger/
    retry/
    reprocess/
    metrics/

  tests/


==================================================
2. 폴더별 역할
==================================================

2.1 app/handlers
- 실행 진입점
- 배치 단위 또는 stage 단위 실행 요청을 받는다
- 입력 파라미터를 해석하고 pipeline 또는 stage를 호출한다
- 정책 판단은 하지 않는다

예시 파일명
- daily_collection_handler.py
- raw_collection_handler.py
- candidate_parsing_handler.py
- validation_normalization_handler.py
- load_handler.py
- fail_classification_handler.py


2.2 app/pipeline
- 여러 stage를 순서대로 연결하는 orchestration 역할
- 전체 일일 실행 흐름을 제어한다
- 개별 비즈니스 처리 로직은 직접 갖지 않는다

예시 파일명
- daily_collection_pipeline.py
- retry_pipeline.py
- reprocess_pipeline.py


2.3 app/exceptions
- 시스템 예외 클래스 정의
- exception은 실패 의미와 context만 가진다
- action, retry_count, severity는 직접 가지지 않는다

예시 파일명
- base_exceptions.py
- collection_exceptions.py
- parsing_exceptions.py
- validation_exceptions.py
- load_exceptions.py


2.4 app/policies
- 정책 기준 정의
- reason_code별 기본 정책 설명
- 문서성/정책성 구조 보관
- 실제 최종 판단은 resolver가 수행한다

예시 파일명
- failure_policy.py
- retry_policy.py
- monitoring_policy.py
- lifecycle_policy.py


2.5 app/enums
- 문자열 상수 집합
- Enum 또는 그에 준하는 상수 그룹 관리
- 운영 의미가 고정된 코드만 보관한다

예시 파일명
- reason_code.py
- action_type.py
- stage_type.py
- entity_type.py
- status_type.py
- collector_type.py


2.6 app/models
- 데이터 구조 정의
- stage input/output
- fail record
- warning record
- dedup result
- load result 등 JSONL 레코드 단위의 구조를 담당한다

예시 파일명
- common_models.py
- target_models.py
- raw_models.py
- candidate_models.py
- normalized_models.py
- load_models.py
- fail_models.py
- metrics_models.py


2.7 app/stages
- 각 stage의 실제 처리 책임을 가진다
- 입력 모델을 받아 출력 모델을 생성한다
- 정책 판단은 하지 않고 exception을 발생시키거나 결과를 반환한다

예시 파일명
- target_selection_stage.py
- raw_collection_stage.py
- candidate_parsing_stage.py
- validation_normalization_stage.py
- load_stage.py
- fail_classification_stage.py


2.8 app/resolvers
- reason_code + stage + entity_type 기준으로 action을 결정한다
- policy source of truth 역할
- stage는 resolver 결과만 사용한다

예시 파일명
- failure_resolver.py
- monitoring_resolver.py
- lifecycle_resolver.py


2.9 app/storage
- JSONL 읽기/쓰기
- 파일 경로 생성
- raw/candidate/normalized/fail ledger 저장 담당
- overwrite 금지 정책 등 저장 규칙 관리

예시 파일명
- path_builder.py
- jsonl_writer.py
- jsonl_reader.py
- raw_file_writer.py
- metrics_writer.py


2.10 app/logging
- logger 설정
- 구조화 로그 포맷 정의
- logger wrapper를 만들기보다 설정 중심으로 관리

예시 파일명
- logging_config.py
- log_formatter.py


2.11 app/utils
- 공통 유틸
- 시간, ID 생성, 해시, 문자열 정규화 보조 기능

예시 파일명
- time_utils.py
- id_utils.py
- hash_utils.py
- text_utils.py


2.12 app/config
- 환경 설정
- 실행에 필요한 설정값 주입
- 민감 정보는 직접 저장하지 않는다

예시 파일명
- settings.py


==================================================
3. 데이터 저장 폴더 구조
==================================================

data/
  raw/
  candidate/
  normalized/
  fail_ledger/
  retry/
  reprocess/
  metrics/

설명:
- raw/: 수집 원본 html/json/text
- candidate/: 파싱 결과 후보 JSONL
- normalized/: 정규화 결과 JSONL
- fail_ledger/: 실패 기록 JSONL
- retry/: 다음날 retry 대상 JSONL
- reprocess/: 재처리 대상 JSONL
- metrics/: 집계 지표 파일

권장 경로 원칙:
- 날짜 기준 디렉터리 분리
- category_cd 분리 가능
- batch_id 분리 가능
- overwrite 금지


==================================================
4. 핵심 클래스 구조
==================================================

4.1 Base Exception 구조

클래스명:
- CrawlerException

역할:
- 모든 크롤링 예외의 부모 클래스

필수 필드:
- reason_code
- stage
- entity_type
- detail
- message

원칙:
- action 없음
- retry_count 없음
- severity 없음

하위 클래스 예시:
- NetworkError
- TimeoutError
- SelectorMismatchError
- EmptyExtractionError
- MissingNormalizedAddressError
- MapInsertFailedError


4.2 FailurePolicyResolution 클래스

역할:
- resolver가 판단한 결과를 담는 구조

필수 필드:
- reason_code
- stage
- entity_type
- action
- severity
- max_retry_count
- include_in_next_batch
- alert_required

설명:
- Exception이 아니라 Resolver 출력 모델이다


4.3 FailureResolver 클래스

역할:
- reason_code + stage + entity_type 기준 정책 판단

입력:
- exception 또는 실패 context

출력:
- FailurePolicyResolution

핵심 책임:
- action 결정
- severity 결정
- retry 가능 여부 결정
- 다음 batch 포함 여부 결정

원칙:
- 시스템 내 실제 정책 판단의 source of truth


4.4 FailRecord 클래스

역할:
- fail ledger JSONL 한 줄 단위 구조

필수 필드:
- batch_id
- target_date
- stage
- entity_type
- entity_id
- reason_code
- action
- severity
- retry_count
- failed_at

권장 필드:
- category_cd
- source_url
- raw_path
- processed_path
- detail
- dedup_key_type
- dedup_key_value

중복 방지 키:
- (batch_id, stage, entity_type, entity_id, reason_code)


4.5 WarningRecord 클래스

역할:
- 실패는 아니지만 품질 이슈를 기록

필수 필드:
- batch_id
- stage
- entity_type
- entity_id
- reason_code
- created_at

예시:
- AMBIGUOUS_MENU_NAME
- UNDEFINED_CODE_DETECTED


4.6 DedupKey 클래스

역할:
- dedup 판정에 사용되는 키 구조

필수 필드:
- dedup_key_type
- dedup_key_value
- dedup_rule_version

권장 필드:
- canonical_url
- normalized_name
- normalized_address
- source_platform
- source_internal_id
- dedup_conflict_flag


4.7 EntityCompleteness 클래스

역할:
- load 결과에서 데이터 완성도를 표현

필드 예시:
- menu_expected_count
- menu_loaded_count
- review_expected_count
- review_loaded_count
- completeness_score

설명:
- business_success_flag 대신 수치형 completeness 중심으로 관리


4.8 LoadResultRecord 클래스

역할:
- load 결과 JSONL 구조

필수 필드:
- batch_id
- target_id
- entity_id
- store_load_status
- partial_failure_flag
- entity_completeness
- loaded_at

권장 필드:
- warning_reason_codes
- menu_load_summary
- review_load_summary
- dedup_key_type
- dedup_key_value


==================================================
5. Stage별 입력/출력 클래스 설계
==================================================

5.1 Stage 0 - Daily Target Selection

입력 클래스:
- DailyTargetSelectionInput

필드:
- target_date
- category_cd
- target_count
- selection_policy

출력 클래스:
- DailyTargetSelectionResult

필드:
- batch_id
- target_date
- category_cd
- selected_targets
- selection_summary
- output_path

하위 레코드:
- TargetCandidateRecord


5.2 Stage 1 - Raw Collection

입력 클래스:
- RawCollectionInput

필드:
- batch_id
- target_date
- category_cd
- shard_id
- assigned_targets

출력 클래스:
- RawCollectionResult

필드:
- batch_id
- shard_id
- raw_results
- summary
- output_path

하위 레코드:
- RawCollectionRecord

필수 필드:
- target_id
- source_url
- collector_type
- raw_path
- collected_at
- status


5.3 Stage 2 - Candidate Parsing

입력 클래스:
- CandidateParsingInput

필드:
- batch_id
- category_cd
- raw_metadata_path

출력 클래스:
- CandidateParsingResult

필드:
- batch_id
- candidate_results
- summary
- output_path

하위 레코드:
- CandidateRecord
- MenuCandidateRecord
- ReviewCandidateRecord


5.4 Stage 3 - Validation & Normalization

입력 클래스:
- ValidationNormalizationInput

필드:
- batch_id
- category_cd
- candidate_path
- dedup_rule_version

출력 클래스:
- ValidationNormalizationResult

필드:
- batch_id
- normalized_results
- summary
- output_path
- warning_output_path

하위 레코드:
- NormalizedStoreRecord
- NormalizedMenuRecord
- CodeResolutionRecord
- DedupKey


5.5 Stage 4 - Load

입력 클래스:
- LoadStageInput

필드:
- batch_id
- category_cd
- normalized_path

출력 클래스:
- LoadStageResult

필드:
- batch_id
- load_results
- summary
- output_path
- warning_output_path
- fail_output_path

하위 레코드:
- LoadResultRecord
- EntityCompleteness


5.6 Stage 5 - Fail Classification

입력 클래스:
- FailClassificationInput

필드:
- batch_id
- category_cd
- fail_sources
- warning_sources

출력 클래스:
- FailClassificationResult

필드:
- batch_id
- fail_ledger_path
- retry_items_path
- reprocess_items_path
- warning_summary_path
- summary

하위 레코드:
- RetryItemRecord
- ReprocessItemRecord
- FailRecord


==================================================
6. Enum 구조 설계
==================================================

6.1 ReasonCode
예시:
- NETWORK_ERROR
- TIMEOUT
- SELECTOR_MISMATCH
- EMPTY_EXTRACTION
- AMBIGUOUS_MENU_NAME
- UNDEFINED_CODE_DETECTED
- MISSING_NORMALIZED_NAME
- MISSING_NORMALIZED_ADDRESS
- DEDUP_KEY_NOT_GENERATABLE
- CONFLICTING_DEDUP_SIGNALS
- MAP_INSERT_FAILED
- MENU_INSERT_FAILED
- CRAWLING_INSERT_FAILED
- UNKNOWN_REASON_CODE

원칙:
- reason_code는 Enum으로 관리
- 동일 의미의 문자열 중복 금지


6.2 ActionType
- RETRY
- REPROCESS_AUTO
- REPROCESS_MANUAL
- DROP
- LOAD_WITH_WARNING
- ALERT_ONLY


6.3 StageType
- TARGET_SELECTION
- RAW_COLLECTION
- CANDIDATE_PARSING
- VALIDATION_NORMALIZATION
- LOAD
- FAIL_CLASSIFICATION


6.4 EntityType
- STORE
- MENU
- REVIEW
- MAP
- CRAWLING
- COMMON


==================================================
7. Storage 클래스 설계
==================================================

7.1 PathBuilder 클래스

역할:
- 저장 경로 생성

입력:
- stage
- category_cd
- target_date
- batch_id
- status

출력:
- 저장 경로 문자열

원칙:
- overwrite 금지
- 경로 생성 규칙 일관 유지


7.2 JsonlWriter 클래스

역할:
- JSONL 파일 저장

책임:
- 한 줄씩 append 또는 새 파일 생성
- overwrite 방지
- utf-8 저장


7.3 JsonlReader 클래스

역할:
- JSONL 파일 읽기

책임:
- 한 줄 단위 순회
- 유효성 검증 보조 가능


7.4 RawFileWriter 클래스

역할:
- html/json/text 원본 저장

원칙:
- 원본 증거 보존
- overwrite 금지
- 신규 파일 생성


7.5 MetricsWriter 클래스

역할:
- batch별 경량 지표 저장

지표 예시:
- raw_success_rate
- parsing_success_rate
- validation_pass_rate
- load_success_rate
- fail_count_by_reason_code
- retry_recovery_rate


==================================================
8. Resolver 구조 설계
==================================================

8.1 FailureResolver
- 실패 정책 판정 전담

8.2 MonitoringResolver
- 알람 조건 판정
- fail_count
- fail_rate
- load_success_rate 기준 사용

8.3 LifecycleResolver
- 파일 수명 주기 관리
- raw 30일
- candidate 14일
- normalized 30일
- fail ledger 90일
- metrics 영구


==================================================
9. 구현 시 금지 원칙
==================================================

1) stage 내부에서 if reason_code == ... 로 직접 action 판단 금지
2) exception class에 retry_count, severity 직접 보관 금지
3) raw overwrite 금지
4) global mutable cache 금지
5) cookie, auth header 저장 금지
6) JSONL 구조를 stage마다 임의 변경 금지


==================================================
10. 지금 단계에서 확정된 것 / 보류된 것
==================================================

확정:
- JSONL 저장 구조
- 폴더 구조
- class 책임 분리
- exception / resolver / fail record 분리
- dedup_rule_version 필수
- partial_failure_flag 사용
- entity_completeness 사용

보류:
- 실제 메서드 시그니처 상세
- 실제 파일명 규칙의 초 단위 형식
- metrics 파일 포맷(csv/json)
- raw 압축 방식
- 실제 구현 언어 세부 문법


==================================================
11. 최종 결론
==================================================

본 구조는 다음 순서로 구현 가능한 상태를 목표로 확정한다.

1) Enum 정의
2) Model 클래스 정의
3) Exception 클래스 정의
4) Resolver 클래스 정의
5) Storage 클래스 정의
6) Stage 클래스 정의
7) Handler / Pipeline 연결

즉, 현재는
“DB 테이블 없이도 JSONL 기반 운영이 가능한 구조 설계”
까지 완료된 상태로 본다.

==================================================
[END]
==================================================