[Stage 함수 I/O 정의 원칙]

1. 각 stage 함수는 한 단계의 책임만 가진다.
2. 각 stage 함수는 입력(Input), 출력(Output), 산출물 저장 경로, 실패 기록 항목을 명시적으로 정의한다.
3. 상태 간 전달은 file/S3 path + 명시적 payload 방식으로 수행한다.
4. 특정 stage만 독립 재실행할 수 있도록 출력 포맷을 고정한다.
5. logger 출력과 fail ledger 기록은 분리한다.
6. 실패 시 None 반환이 아니라 구조화된 결과 또는 ledger 기록 기준을 따른다.
7. 수집 대상이 대량일 경우 Stage 1은 Fan-out 구조를 통해 shard 단위로 병렬 실행할 수 있어야 한다.
8. 코드 테이블에 존재하지 않는 값이 식별될 경우, 시스템은 즉시 전체 실패 처리하지 않고 UNKNOWN 코드 치환 정책을 적용할 수 있어야 한다.
9. UNKNOWN 코드 치환이 발생한 경우 원본 값(raw value), 치환 코드, reason_code를 구조적으로 기록해야 한다.
10. batch 운영 기준으로 사용되는 category_cd와 정규화 결과로 해석된 category 코드는 필요 시 분리하여 관리한다.

==================================================
[Stage 0. Daily Target Selection]
==================================================

함수명 예시
- run_daily_target_selection()
- select_daily_targets()

1. 책임
- category_cd별 당일 수집 대상 store를 선정한다.
- 이미 성공 적재된 store를 제외한다.
- batch_id를 생성한다.
- 이후 stage들이 사용할 target metadata를 생성한다.

2. 입력(Input)
- target_date: 당일 배치 기준 날짜
- category_cd: 대상 카테고리 코드
- target_count: 목표 건수 (기본 100)
- code_table_repository: category_cd 유효성 및 코드 테이블 조회용 객체
- store_repository: 기존 성공 적재 store 조회용 객체
- fail_repository: 실패 이력 및 마지막 reason/action 조회용 객체
- source_pool_provider: 수집 후보 source 제공 객체
- selection_policy:
  - exclude_success_loaded_store: bool
  - allow_retry_by_reason_code: bool
  - daily_success_target_count: int

3. 출력(Output)
- DailyTargetSelectionResult

예시 구조:
{
  "batch_id": "20260422_CA01_001",
  "target_date": "2026-04-22",
  "category_cd": "CA01",
  "target_count": 100,
  "selected_targets": [
    {
      "target_id": "target_001",
      "source_platform": "naver_map",
      "source_url": "https://...",
      "source_internal_id": "12345",
      "selection_reason": "new_candidate"
    }
  ],
  "selection_summary": {
    "candidate_pool_count": 180,
    "excluded_success_store_count": 42,
    "retry_candidate_count": 12,
    "final_selected_count": 100
  }
}

4. 성공 산출물 저장 위치
- target metadata json/jsonl
- 예:
  crawling=target/service=shop/year=2026/month=04/day=22/status=success/category_cd=CA01/stage=target_selection/batch_id=20260422_CA01_001/targets.json

5. 실패 시 기록 항목
- status = fail
- stage = target_selection
- reason_code
- reason_detail
- category_cd
- target_date
- batch_id (생성 가능 시 포함)

6. 다음 stage 전달값
- batch_id
- category_cd
- target_date
- selected_targets_path
- selection_summary

7. 재실행 시 주의사항
- 동일 batch_id 재실행인지, 새 seq 발급 batch인지 구분해야 한다.
- source pool이 바뀌더라도 기존 batch 재실행이면 같은 target list를 재사용하는 정책이 필요하다.
==================================================
[Stage 1. Raw Collection - 수정본]
==================================================

함수명 예시
- run_raw_collection_shard()
- collect_raw_for_assigned_targets()
- collect_raw_shard()

1. 책임
- Stage 0에서 생성된 selected_targets 중 일부 assigned_targets만 처리한다.
- assigned_targets에 대해 실제 raw 수집을 수행한다.
- 원시 응답(html/json/text)을 증거 보존 형태로 저장한다.
- collector_type(http/render/public_source)을 기록한다.
- shard 단위의 성공/실패를 독립 추적한다.

2. 입력(Input)
- batch_id
- target_date
- category_cd
- shard_id
- shard_seq
- assigned_targets
- collector_factory 또는 collector 객체
- storage_writer
- path_builder
- request_config
- execution_context

assigned_targets 예시:
[
  {
    "target_id": "target_021",
    "source_platform": "naver_map",
    "source_url": "https://...",
    "source_internal_id": "12345"
  },
  {
    "target_id": "target_022",
    "source_platform": "kakao_map",
    "source_url": "https://...",
    "source_internal_id": "99887"
  }
]

3. 출력(Output)
- RawCollectionShardResult

예시 구조:
{
  "batch_id": "20260422_CA01_001",
  "target_date": "2026-04-22",
  "category_cd": "CA01",
  "shard_id": "raw_CA01_003",
  "shard_seq": 3,
  "raw_results": [
    {
      "target_id": "target_021",
      "source_url": "https://...",
      "collector_type": "http",
      "collected_at": "2026-04-22T10:00:00+09:00",
      "raw_path": "crawling=raw/service=shop/year=2026/month=04/day=22/status=success/category_cd=CA01/stage=raw_collection/batch_id=20260422_CA01_001/shard_id=raw_CA01_003/target_021.html",
      "http_status": 200,
      "status": "success"
    }
  ],
  "summary": {
    "assigned_target_count": 10,
    "success_count": 8,
    "fail_count": 2
  }
}

4. 성공 산출물 저장 위치
- raw html/json/text 파일
- shard 단위 raw metadata jsonl

예시:
crawling=raw/service=shop/year=2026/month=04/day=22/status=success/category_cd=CA01/stage=raw_collection/batch_id=20260422_CA01_001/shard_id=raw_CA01_003/...

5. 실패 시 기록 항목
- stage = raw_collection
- batch_id
- shard_id
- target_id
- source_url
- reason_code
- reason_detail
- action
- retry_count
- last_attempt_at

6. 다음 stage 전달값
- batch_id
- category_cd
- shard_id
- raw shard metadata path
- raw success item path list

7. 재실행 시 주의사항
- 재실행은 batch 전체가 아니라 shard 단위로 가능해야 한다.
- 동일 batch_id 내에서 shard_id는 유일해야 한다.
- 한 shard의 실패가 다른 shard 처리에 영향을 주지 않아야 한다.
==================================================
[Stage 2. Candidate Parsing]
==================================================

함수명 예시
- run_candidate_parsing()
- parse_candidates()
- parse_candidate()

1. 책임
- raw 산출물을 읽어 store/menu/review 후보 데이터를 추출한다.
- raw의 증거성은 유지한다.
- selector/DOM 기반 추출 실패 시 상세 실패 정보를 남긴다.

2. 입력(Input)
- batch_id
- target_date
- category_cd
- raw_metadata_path
- parser_registry 또는 parser 객체
- storage_reader
- storage_writer

3. 출력(Output)
- CandidateParsingResult

예시 구조:
{
  "batch_id": "20260422_CA01_001",
  "category_cd": "CA01",
  "candidate_results": [
    {
      "target_id": "target_001",
      "source_url": "https://...",
      "raw_path": "...",
      "store_candidates": {
        "raw_name": "맛있는초밥 본점",
        "raw_address": "서울 강남구 ..."
      },
      "menu_candidates": [
        {
          "menu_name_raw": "모듬초밥",
          "price_raw": "15000"
        }
      ],
      "review_candidates": [
        {
          "review_text_raw": "맛있어요",
          "review_date_raw": "2026.04.21"
        }
      ],
      "status": "success"
    }
  ]
}

4. 성공 산출물 저장 위치
- candidate jsonl

5. 실패 시 기록 항목
- stage = candidate_parsing
- raw_path
- selector_name
- dom_detail
- reason_code (예: SELECTOR_MISMATCH)
- reason_detail
- action

6. 다음 stage 전달값
- batch_id
- candidate jsonl path

7. 재실행 시 주의사항
- parsing 재실행은 raw_path만 있으면 가능해야 한다.
- raw 원본은 수정하지 않는다.
==================================================
[Stage 3. Validation & Normalization - 수정본]
==================================================

함수명 예시
- run_validation_normalization()
- validate_and_normalize()

1. 책임
- candidate 데이터를 검증한다.
- store/menu/review를 정규화한다.
- 코드 테이블을 DB 조회 기반으로 검증한다.
- dedup 판정에 필요한 필드를 생성한다.
- 코드 미정의 값이 발견되면 UNKNOWN 코드 치환 정책을 적용할 수 있다.
- UNKNOWN 치환 발생 시 원본 값과 치환 결과를 구조적으로 기록한다.

2. 입력(Input)
- batch_id
- target_date
- category_cd
- candidate_path
- code_table_repository
- validator_registry
- normalization_rules
- execution_scope_cache
- storage_reader
- storage_writer

3. 출력(Output)
- ValidationNormalizationResult

예시 구조:
{
  "batch_id": "20260422_CA01_001",
  "target_date": "2026-04-22",
  "category_cd": "CA01",
  "normalized_results": [
    {
      "target_id": "target_021",
      "store": {
        "target_category_cd": "CA01",
        "normalized_category_cd": "ETC",
        "normalized_name": "맛있는초밥 본점",
        "normalized_address": "서울특별시 강남구 ...",
        "normalized_address_cd": "LA999",
        "canonical_url": "https://example.com/store/123",
        "source_platform": "naver_map",
        "source_internal_id": "12345"
      },
      "menus": [
        {
          "menu_name_raw": "대표",
          "menu_name_normalized": null,
          "reason_code": "AMBIGUOUS_MENU_NAME"
        }
      ],
      "reviews": [],
      "dedup_key_candidates": {
        "canonical_url": "https://example.com/store/123",
        "name_address": "맛있는초밥 본점|서울특별시 강남구 ...",
        "platform_internal_id": "naver_map|12345"
      },
      "code_resolution": {
        "category": {
          "raw_value": "퓨전오마카세",
          "resolved_code": "ETC",
          "reason_code": "UNDEFINED_CODE_DETECTED"
        },
        "address": {
          "raw_value": "서울 강남구 역삼동",
          "resolved_code": "LA999",
          "reason_code": "UNDEFINED_CODE_DETECTED"
        }
      },
      "status": "success_with_warning"
    }
  ]
}

4. 성공 산출물 저장 위치
- normalized jsonl
- code resolution warning jsonl 또는 fail/warning ledger entry

5. 실패 시 기록 항목
- stage = validation_normalization
- reason_code
- reason_detail
- invalid_field
- raw_value
- resolved_code (존재 시)
- action

6. 다음 stage 전달값
- batch_id
- normalized_path
- code resolution warning summary path

7. 재실행 시 주의사항
- 코드 테이블 값은 상수화하지 않는다.
- 동일 실행 내 캐시는 허용하지만 global cache는 금지한다.
- batch 운영 기준 category_cd는 유지하고, 정규화 결과 category는 별도 필드로 관리할 수 있다.
==================================================
[Stage 4. Load - 수정본]
==================================================

함수명 예시
- run_load()
- load_to_db()

1. 책임
- normalized 데이터를 DB에 적재한다.
- 적재 전 코드 테이블 참조 무결성을 확인한다.
- store는 upsert 정책으로 적재한다.
- menu/review는 종속 엔티티 기준으로 분리 적재한다.
- UNKNOWN 코드로 치환된 데이터도 참조 무결성을 만족하면 정상 적재를 시도한다.
- store 성공 / menu-review 일부 실패 / warning 적재를 구분 기록한다.

2. 입력(Input)
- batch_id
- target_date
- category_cd
- normalized_path
- db_session
- code_table_repository
- store_repository
- menu_repository
- review_repository
- query_constants
- execution_context

3. 출력(Output)
- LoadResult

예시 구조:
{
  "batch_id": "20260422_CA01_001",
  "category_cd": "CA01",
  "load_results": [
    {
      "target_id": "target_021",
      "store_load_status": "success",
      "store_id": "store_123",
      "store_upsert_mode": "update",
      "warning_flags": [
        "UNDEFINED_CODE_DETECTED"
      ],
      "menu_load_summary": {
        "success_count": 5,
        "fail_count": 1
      },
      "review_load_summary": {
        "success_count": 10,
        "fail_count": 0
      }
    }
  ],
  "summary": {
    "store_success_count": 82,
    "store_fail_count": 18,
    "success_with_warning_count": 7
  }
}

4. 성공 산출물 저장 위치
- load result jsonl
- warning 포함 적재 요약 파일

5. 실패 시 기록 항목
- stage = load
- entity_type = store/menu/review
- entity_id 또는 source key
- reason_code
- reason_detail
- action
- retry_count

6. 다음 stage 전달값
- batch_id
- load result path
- fail item path
- warning summary path

7. 재실행 시 주의사항
- 동일 store 중복 insert 방지를 위해 unique key 또는 upsert 정책을 적용한다.
- store 실패는 store 전체 실패로 본다.
- store 성공 후 menu/review 일부 실패는 종속 엔티티 fail ledger로 분리 기록한다.
- UNKNOWN 코드 치환은 적재 허용 대상이지만, 운영 요약에서는 별도 집계해야 한다.

==================================================
[Stage 5. Fail Classification / Retry Scheduling - 수정본]
==================================================

함수명 예시
- run_fail_classification()
- classify_failures_and_schedule_retry()

1. 책임
- 각 stage의 실패를 reason_code/action 기준으로 분류한다.
- retry / reprocess / drop 대상을 결정한다.
- warning 성격의 운영 이슈를 별도로 집계한다.
- 다음 실행 핸들러가 읽을 수 있는 상태 파일을 생성한다.
- retry_count, 마지막 실패 시간, 마지막 reason_code를 누적 관리한다.

2. 입력(Input)
- batch_id
- target_date
- category_cd
- fail_sources:
  - raw fail records
  - parsing fail records
  - validation fail records
  - load fail records
- warning_sources:
  - undefined code detected records
  - success_with_warning records
- fail_repository
- storage_reader
- storage_writer

3. 출력(Output)
- FailClassificationResult

예시 구조:
{
  "batch_id": "20260422_CA01_001",
  "category_cd": "CA01",
  "fail_ledger_path": ".../fail_ledger.jsonl",
  "retry_items_path": ".../retry_items.jsonl",
  "reprocess_items_path": ".../reprocess_items.jsonl",
  "drop_items_path": ".../drop_items.jsonl",
  "warning_summary_path": ".../warning_summary.json",
  "summary": {
    "retry_count": 10,
    "reprocess_count": 4,
    "drop_count": 3,
    "undefined_code_detected_count": 7
  }
}

4. 성공 산출물 저장 위치
- fail_ledger.jsonl
- retry_items.jsonl
- reprocess_items.jsonl
- drop_items.jsonl
- warning_summary.json

5. 실패/경고 시 기록 항목
- stage = fail_classification
- reason_code
- reason_detail
- source_fail_record_path
- severity
- action

6. 다음 stage 전달값
- 다음날 target selection에서 재사용할 retry/reprocess 대상 목록
- 운영 알람용 fail summary
- 코드 테이블 보강 필요 warning summary

7. 재실행 시 주의사항
- 같은 fail 이벤트가 중복 기록되지 않도록 idempotency 기준이 필요하다.
- status가 아니라 reason_code/action 기준으로 재포함 여부를 판단한다.
- UNDEFINED_CODE_DETECTED는 기본적으로 운영 보강 warning으로 집계하되, 정책상 필요하면 별도 재처리 대상으로 승격할 수 있다.
==================================================
[운영 및 확장성 추가 원칙]
==================================================

1. 리소스 가용성 및 병렬 수집
수집 대상이 대량일 경우 Stage 1 Raw Collection은 Fan-out 구조를 통해 병렬 실행한다.
Stage 0에서 생성된 selected_targets는 단일 대형 작업으로 처리하지 않고, shard 단위의 assigned_targets로 분할하여 개별 실행 단위에 전달한다.
각 Stage 1 실행 인스턴스는 자신에게 할당된 assigned_targets만 처리하며, shard_id를 기준으로 로그, 산출물, 실패 이력을 추적할 수 있어야 한다.

2. 코드 미정의 값 대응
Validation & Normalization 단계에서 코드 테이블에 존재하지 않는 신규 값이 식별될 경우, 즉시 전체 실패 처리하지 않고 시스템 표준 UNKNOWN 코드로 치환할 수 있다.
이 경우 원본 값(raw value), 치환된 코드, reason_code=UNDEFINED_CODE_DETECTED를 구조적으로 기록해야 한다.

3. 운영 기준 코드와 정규화 코드의 분리
배치 운영 기준으로 사용되는 category_cd와 정규화 과정에서 해석된 코드값은 구분하여 관리할 수 있다.
특히 daily target selection 기준 category_cd는 배치 운영 축으로 유지하고, 정규화 결과 신규 코드 미정의가 발생한 경우에는 별도의 normalized_category_cd 또는 대응 필드를 통해 UNKNOWN 치환 결과를 기록한다.

4. Graceful Load 및 운영 알림
UNKNOWN 코드로 치환된 데이터는 참조 무결성을 만족하는 범위 내에서 정상 적재를 시도한다.
Fail Classification 또는 운영 요약 단계에서는 UNDEFINED_CODE_DETECTED 집계를 별도로 산출하여 운영자에게 코드 테이블 보강 필요성을 알린다.

[Stage 공통 실패 처리 원칙 - 변경]

* 각 stage는 내부 실패 발생 시 Exception class를 발생시킨다.

* Exception class는 reason_code를 포함해야 한다.

* Fail 처리 흐름:
  Exception 발생
  → Resolver를 통해 action 결정
  → Fail Ledger 기록
  → CloudWatch 로그 출력

* Stage는 정책 판단을 직접 수행하지 않는다.

* Stage는 Exception을 전달하고 결과만 기록한다.
