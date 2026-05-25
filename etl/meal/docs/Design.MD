크롤링 최종 통합 설계안 (최종 확정본)
작성일: 2026-04-23

==================================================
0. 문서 목적
==================================================

본 문서는 지금까지 확정된 크롤링 관련 설계 문서들과 2026-04-23 대화에서 최종 확정한 운영 규칙을 통합한 최종 설계안이다.

이 문서의 목적은 다음과 같다.

1) 구현 시 다른 길로 가지 않도록 설계 기준을 고정한다.
2) 구조, 정책, 책임 분리, 운영 규칙을 하나의 문서로 통합한다.
3) 구현자, 리뷰어, 운영자가 동일한 기준으로 판단할 수 있도록 한다.
4) 이후 상세 구현, 테스트, 코드 리뷰의 기준 문서로 사용한다.

본 문서는 구현 코드가 아니라 설계 기준서이다.
다만 실제 구현 시 반드시 따라야 하는 불변 규칙과 운영 원칙을 포함한다.

==================================================
1. 설계 철학
==================================================

핵심 철학은 다음과 같다.

1) Stage는 데이터 처리만 담당한다.
2) 정책 판단은 Resolver가 담당한다.
3) Exception은 실패 의미만 표현한다.
4) Fail Ledger는 운영 기록을 담당한다.
5) Logger는 실행 로그이며, 운영 데이터와 분리한다.
6) 코드 테이블 값은 하드코딩하지 않고 반드시 DB 조회 기반으로 처리한다.
7) SQL 쿼리문은 상수화한다.
8) JSONL 중심 구조로 중간 산출물을 관리한다.
9) AWS 환경에서 비용, 재실행, 관측성을 고려한 구조로 설계한다.

핵심 원칙 문장:

- 정책은 코드에 하드코딩하지 않는다.
- 정책 판단은 Resolver에서만 수행한다.
- Stage는 정책을 직접 판단하지 않는다.
- 같은 의미의 실패는 같은 reason_code를 사용한다.
- 운영 기준은 status가 아니라 reason_code/action 기준으로 해석한다.

==================================================
2. 전체 파이프라인 구조 (수정)
==================================================

전체 시스템은 4개의 독립 프로젝트로 구성된다.

1. crawl project
2. process project
3. save project
4. failcheck project

기존 Stage 구조:
Stage 0: Daily Target Selection
Stage 1: Raw Collection
Stage 2: Candidate Parsing
Stage 3: Validation & Normalization
Stage 4: Load
Stage 5: Fail Classification / Retry Scheduling

변경:
- Stage 개념은 유지한다.
- Stage의 책임을 프로젝트 단위로 재배치한다.

매핑:
Stage 1 → crawl project  
Stage 2,3 → process project  
Stage 4 → save project  
Stage 5 → failcheck project  

==================================================
2.1 프로젝트 기반 실행 구조 (신규)
==================================================

crawl project
→ process project
→ save project

failcheck project
→ crawl/process/save fail 데이터를 기반으로 후속 판단 수행

각 프로젝트는 독립 실행되며 직접 호출되지 않는다.

==================================================
2.2 프로젝트 간 연결 방식 (신규)
==================================================

연결 기준:
- 날짜 기반 폴더
- success / fail 디렉토리
- JSONL 파일
- metadata

흐름:

crawl success → process 입력  
process success → save 입력  
crawl/process/save fail → failcheck 입력  

==================================================
2.3 날짜 기준 실행 원칙 (신규)
==================================================

process:
- crawl success 없으면 실행하지 않음

save:
- process success 없으면 실행하지 않음

중요:
- 실행 대상 없음은 fail이 아니다
- fail 기록 금지

==================================================
3. 공통 책임 분리 (보완)
==================================================

3.1 Stage
- 데이터 처리만 수행
- 정책 판단 금지

3.2 Exception
- 실패 의미만 표현

3.3 Resolver
- action 결정

3.4 Fail Ledger
- 실패 기록

3.5 Logger
- 실행 로그

3.6 Project 책임 (신규)

crawl:
- 수집 + raw 저장

process:
- parsing + normalization

save:
- DB 적재

failcheck:
- 실패 기반 후속 판단

3.7 프로젝트 정책 제한 (신규)
다음 금지:

- crawl에서 retry 판단 금지
- process에서 retry/reprocess 판단 금지
- save에서 retry/reprocess 판단 금지
- crawl/process/save에서 alert 발송 금지

정책 판단은 failcheck + Resolver만 수행

==================================================
4. 저장 구조 원칙
==================================================

중간 산출물은 JSONL 중심으로 관리한다.

Raw:
- html / json / text
- 원본 증거 보존 목적
- overwrite 금지

Candidate:
- JSONL

Normalized:
- JSONL

Fail Ledger:
- JSONL

Retry / Reprocess 대상:
- JSONL

Metrics:
- 경량 파일
- stage별 lightweight + batch summary 병행

==================================================
5. AWS / 실행 구조 원칙
==================================================

1) AWS Lambda 또는 Lambda 기반 핸들러 실행 가능 구조를 전제로 한다.
2) 공통 모듈은 Layer 또는 재사용 가능한 패키지 구조로 관리 가능해야 한다.
3) global mutable state는 금지한다.
4) 실행 단위는 handler / stage / shard 기준으로 분리 가능해야 한다.
5) AWS 비용을 고려하여 불필요한 재시도, 과도한 로깅, 중복 로직을 줄인다.
6) 반복되는 코드는 공통 유틸 / resolver / collector / repository / storage 계층으로 분리한다.

==================================================
6. 수집 대상 선정 원칙
==================================================

6.1 기본 방향

맛집에 대한 수집은 target.csv를 1차 seed로 사용하는 방향으로 진행한다.

target.csv에는 최소한 다음 정보가 포함될 수 있다.

- address_cd
- shop_cd
- 기타 수집 seed 정보

단, target.csv만으로 전체 구조를 고정하지 않는다.

최종 원칙:
- target.csv = 1차 seed
- source_pool 확장 가능 구조 유지

즉, 초기 운영에서는 target.csv를 기준으로 크롤링하되, 장기적으로는 신규 후보 source_pool을 확장하여 수집 대상을 넓힐 수 있어야 한다.

6.2 Daily Target Selection 기준

- category_cd별 목표는 최종 DB 적재 성공 store 100건이다.
- 이미 성공 적재된 store는 제외한다.
- retry 대상이 있으면 우선 포함한다.
- retry 대상 수가 목표 건수보다 적으면 부족분은 신규 후보로 보충한다.
- retry 대상이 없으면 신규 후보로 채운다.
- Stage 0 재선정이 발생하면 새로운 batch를 생성한다.

==================================================
7. 코드 테이블 중심 설계 원칙
==================================================

7.1 절대 원칙

다음 값들은 절대로 하드코딩하지 않는다.

- address_cd
- shop_cd
- category_cd
- status_cd
- 기타 코드 테이블 기반 값

반드시 DB 코드 테이블 조회 기반으로 처리한다.

7.2 address_cd 처리 원칙

maps 테이블의 address_cd는 기존 코드 테이블에 저장된 LA+숫자 형식의 코드값을 사용한다.

원칙:
- 코드 테이블에 정의된 주소 범위(예: 시/도/구 단위)는 address_cd로 저장
- 코드 테이블로 해석된 부분은 주소 원문에서 제거
- 남는 상세 주소는 address_detail에 저장

즉,
address_cd = 코드 테이블 기준 표준 코드
address_detail = 나머지 상세 주소

7.3 shop_cd 처리 원칙

shop 테이블의 shop_cd는 음식점 종류에 대한 카테고리 코드이며, 반드시 코드 테이블 기준으로 관리한다.

7.4 reason_code 처리 원칙

reason_code는 코드 내부에서는 다음 구조를 유지한다.

- Enum
- Exception class

즉, reason_code는 "Enum + Exception class" 구조를 유지한다.

추가로 운영/조회 목적의 코드 테이블이나 참조 테이블에 reason_code를 저장할 수는 있으나,
실행 중 정책 분기는 DB 조회값이 아니라 코드 내부의 Enum / Resolver 기준으로 처리한다.

정리:
- 코드 내부: Enum + Exception class 유지
- DB/참조 저장: 가능
- 실행 분기 기준: Resolver

7.5 코드 테이블 캐시 원칙

- 실행 범위 cache 허용
- global cache 금지
- TTL 없음
- handler 실행 시작 시 preload 가능
- 실행 종료 시 폐기

최종 원칙:
- cache scope = handler 실행 단위
- TTL 없음
- retry/reprocess 실행도 항상 새로운 실행 컨텍스트를 사용한다.
- Stage 4 Load 직전에는 코드 테이블 참조 무결성을 반드시 재검증한다.

==================================================
8. 쿼리 / Repository / 효율성 원칙
==================================================

1) SQL 쿼리문은 반드시 상수화한다.
2) 코드 테이블 값 자체는 상수화하지 않는다.
3) DB 조회는 repository 계층을 통해 수행한다.
4) 같은 의미의 코드가 반복 구현되지 않도록 공통 repository / util / resolver를 사용한다.
5) AWS 비용을 고려하여 중복 조회, 불필요한 재시도, 과한 raw 저장, 과한 로그를 줄인다.

==================================================
9. 플랫폼 수집 구조 원칙
==================================================

수집 대상 플랫폼은 최소한 다음을 포함한다.

- NaverCollector
- KakaoCollector
- GoogleCollector
- DiningCodeCollector

원칙:
1) 플랫폼별 수집 코드는 분리한다.
2) 공통 인터페이스 또는 factory 구조를 둔다.
3) 사이트마다 다른 selector / request / parsing 구조를 허용한다.
4) Collector는 플랫폼 특화 수집만 담당하고, 공통 정책 판단은 하지 않는다.

==================================================
10. Dedup 정책
==================================================

동일 store 판정 우선순위는 다음과 같다.

1) canonical_url
2) normalized_name + normalized_address
3) source_platform + source_internal_id

원칙:
- 상위 우선순위 키가 존재하면 하위 키는 기준 판정에 사용하지 않는다.
- 하위 키는 보조 비교 정보로만 저장할 수 있다.
- dedup_key는 dedup_key_type + dedup_key_value 조합으로 관리한다.
- dedup_rule_version을 필수로 둔다.

적용 타이밍:
- Stage 3: dedup key 생성
- Stage 4: 최종 dedup 판정 + upsert

충돌 시:
- CONFLICTING_DEDUP_SIGNALS reason_code 기록
- Resolver가 후속 action을 결정한다.

==================================================
11. batch_id / 재실행 규칙
==================================================

11.1 batch_id 생성 규칙

batch_id는 다음 기본 구조를 따른다.

date + category + seq

예:
20260423_CA01_001

11.2 재실행 기준

최종 확정 원칙:
- 같은 target set에 대한 복구 재실행이면 동일 batch_id 유지
- Stage 0 재선정이 발생하면 새로운 batch_id 발급

11.3 같은 target set 판단 기준

같은 target set 판단의 기본 기준은 selected_targets_path 동일 여부로 본다.

즉:
- selected_targets_path 동일 → 동일 target set → 동일 batch_id 유지 가능
- Stage 0 재선정 발생 → 새로운 target set → 새 batch_id 발급

11.4 run_attempt

동일 batch 재실행 추적을 위해 run_attempt 필드를 둔다.

예:
batch_id = 20260423_CA01_001
run_attempt = 2

11.5 retry / reprocess batch 처리

retry 전용 batch_id를 별도로 만드는 구조는 기본 채택하지 않는다.

최종 원칙:
- retry / reprocess 대상은 일반 batch 흐름에 흡수 가능
- origin_batch_id 또는 batch_type 필드로 출처를 추적한다.

권장 필드:
- origin_batch_id
- batch_type = NORMAL | RETRY | REPROCESS

==================================================
12. shard 전략
==================================================

Stage 1 Raw Collection은 Fan-out 가능 구조로 설계한다.

최종 선택:
- shard당 target 수 고정
- shard 실패 시 재실행 단위는 shard로 고정

예시:
- shard_size = 10
- shard_count = ceil(target_count / shard_size)

원칙:
- 한 shard의 실패가 다른 shard에 영향을 주지 않아야 한다.
- shard_id는 동일 batch 내에서 유일해야 한다.
- 재실행도 shard 기준으로 추적한다.

==================================================
13. entity_id / entity_ref 원칙
==================================================

식별자는 Stage 간에 진화하므로 단일 entity_id만으로 전체를 커버하지 않는다.

최종 원칙:
- entity_id = 해당 stage에서의 대표 key
- entity_ref = 추적용 참조 키 묶음

예시:
- Stage 1~3: target_id 중심
- Stage 4 store: dedup_key 또는 store_id
- menu/review: 종속 엔티티 기준 key

권장 구조:
{
  "entity_id": "target_021",
  "entity_ref": {
    "target_id": "target_021",
    "dedup_key_type": "name_address",
    "dedup_key_value": "맛있는초밥본점|서울특별시강남구테헤란로123",
    "store_id": "store_123"
  }
}

==================================================
14. 실패 처리 구조
==================================================

실패 흐름:

crawl/process/save
→ fail JSONL 저장
→ failcheck project 전달
→ Resolver 판단

14.1 핵심 분리

- Exception = 실패 의미
- Resolver = 정책 판단
- Fail Ledger = 운영 기록
- CloudWatch / logger = 관측

14.2 retry_count

- 실패 발생 즉시 retry_count 증가
- 같은 날 retry 금지
- retry_count >= 5 를 기본 상한으로 둔다.

14.3 종착 action

최종 방향:
- retry_count 초과 후 최종 종착은 reason_code별로 다르게 결정한다.
- 초기에는 핵심 reason_code만 세분화하고, 나머지는 공통 default rule을 둔다.

예시 방향:
- NETWORK_ERROR 계열: retry → 한도 초과 시 별도 종착 규칙
- SELECTOR_MISMATCH: reprocess
- UNDEFINED_CODE_DETECTED: warning 또는 reprocess 후보
- INVALID_URL: drop 가능
- NOT_RESTAURANT_ENTITY: drop 가능

14.4 운영 규칙

- reason_code 추가 승인 주체는 운영진
- 신규 reason_code 추가 시 Resolver 룰도 함께 정의해야 한다.
- Resolver 룰 변경은 별도 배포 프로세스를 따른다.

14.5 failcheck 중심 구조 (신규)

failcheck project 역할:

- fail 데이터 수집
- reason_code 분석
- retry_count 확인
- Resolver 호출
- action 결정

가능 action:

- retry
- reprocess
- alert
- drop
- warning 종료
- manual_check

중요:

failcheck는 후속 판단만 수행한다.

직접 수행 금지:

- 크롤링 금지
- 데이터 전처리 금지
- DB 적재 금지

재처리 방식:

- crawl 실패 → crawl project 재전달
- process 실패 → process project 재전달
- save 실패 → save project 재전달

==================================================
15. Resolver 룰 변경 배포 프로세스
==================================================

최종 채택 방식: 안전한 방식

1) reason_code / resolver 룰 변경안 작성
2) 운영진 승인
3) 정책표 문서 업데이트
4) resolver 코드 수정
5) 테스트 수행
   - reason_code → action 매핑 테스트
   - 회귀 테스트
6) dev 또는 staging 환경 반영
7) 운영 반영
8) 변경 이력 기록

최소 필수 버전:
- 운영진 승인
- 정책표 문서 수정
- resolver 코드 수정
- 매핑 테스트 후 배포

이 프로세스는 운영 정책과 실행 코드가 분리되지 않도록 하기 위한 기준이다.

==================================================
16. Warning 처리 원칙
==================================================

최종 방향:
- warning은 기본적으로 종료 처리
- 특정 reason_code는 reprocess 후보로 승격 가능

명시 확정:
- UNDEFINED_CODE_DETECTED → reprocess 승격 후보
- AMBIGUOUS_MENU_NAME → 기본 warning 유지

즉, 모든 warning을 재처리 대상으로 보지 않는다.
운영상 가치가 있는 warning만 승격한다.

==================================================
17. Load / Transaction 경계
==================================================

원칙:
- store는 핵심 엔티티
- menu / review는 종속 엔티티

트랜잭션 경계:
- store: 1 트랜잭션
- menu: 별도 트랜잭션
- review: 별도 트랜잭션
- image: 별도 트랜잭션
- fail ledger: 비즈니스 트랜잭션과 분리

운영 의미:
- store 적재 실패 → 해당 store 전체 실패
- store 성공 후 menu/review/image 일부 실패 → partial_failure로 기록
- 실패한 종속 엔티티는 fail ledger에 별도 기록 후 후속 처리

Stage 4 Load 전:
- 코드 테이블 참조 무결성 재검증 YES

==================================================
18. 파일 naming / 저장 경로 규칙
==================================================

18.1 경로

Hive 스타일 경로를 사용한다.

기본 구조:

```
crawling={raw|cleansing|save|failcheck}/service={category_cd}/year=YYYY/month=MM/day=DD/stage={stage_name}/batch_id={batch_id}/status={success|fail}
```

원칙:
- `crawling` 파티션은 처리 영역을 나타낸다.
  - crawl raw 저장: `crawling=raw`
  - parsing / normalization 저장: `crawling=cleansing`
  - DB load 결과 저장: `crawling=save`
  - failcheck dispatch / 후속 판단 결과 저장: `crawling=failcheck`
- `service` 파티션은 업무명(`shop`)이 아니라 category_cd 값을 사용한다.
  - 예: `service=CA01`
- 날짜 파티션은 `year=YYYY/month=MM/day=DD` 형식으로 중간에 둔다.
- `status`는 마지막 폴더 분류로 둔다.
- save 영역은 테이블 단위 분리를 위해 날짜 파티션 뒤에 `save={table_name}` 파티션을 추가한다.
  - 예: `save=shop`, `save=menu`, `save=map`, `save=crawling`

예:

```
crawling=raw/service=CA01/year=2026/month=04/day=28/stage=raw_collection/batch_id=20260428_CA01_001/status=success/
crawling=cleansing/service=CA01/year=2026/month=04/day=28/stage=validation_normalization/batch_id=20260428_CA01_001/status=fail/
crawling=save/service=CA01/year=2026/month=04/day=28/save=shop/stage=load/batch_id=20260428_CA01_001/status=success/
crawling=failcheck/service=CA01/year=2026/month=04/day=29/stage=fail_handling/batch_id=20260428_CA01_001/status=pending/
```

18.2 파일명

경로는 Hive 스타일로 충분히 의미를 가지므로 파일명은 timestamp 기반으로 단순화한다.

최종 원칙:
- raw / cleansing / failcheck JSONL 파일명은 YYMMDDHHMMSS.확장자 형식을 기본으로 한다.
- save 영역에서 테이블별 CSV를 생성하는 경우 파일명은 `{table_name}_HHMMSS.csv` 형식을 사용한다.

예:

```
260423101530.html
260423104501.jsonl
shop_153012.csv
menu_153012.csv
map_153012.csv
crawling_153012.csv
```

보완 원칙:
- raw 증거 추적이 필요한 경우 target_id를 보조 메타데이터로 반드시 저장한다.
- 파일명 자체에 target_id를 넣을지는 구현 선택으로 둘 수 있으나, raw metadata에는 target_id를 반드시 남긴다.

18.3 overwrite 금지

- raw overwrite 금지
- JSONL overwrite 금지 또는 신규 파일 생성 기준 유지
- 동일 batch 재실행 시에도 run_attempt / 신규 파일 생성 방식으로 충돌을 피한다.

==================================================
19. Metrics 원칙
==================================================

최종 선택:
- Stage metrics = lightweight
- Batch summary = 최종 집계용

Aggregation 기준:
- batch_id + category_cd 중심
- 필요 시 stage 포함

최종 구조:
1) stage별 경량 metrics 파일
2) batch summary metrics 파일

필수 필드 예시:
- batch_id
- category_cd
- stage
- success_count
- fail_count
- reason_code_count
- raw_success_rate
- parsing_success_rate
- validation_pass_rate
- load_success_rate
- retry_recovery_rate

Metrics는 너무 무겁게 쌓지 않는다.
운영 지표 파일은 일별 및 category별 집계 중심의 경량 포맷으로 저장한다.

==================================================
20. Logger 정책
==================================================

Logger는 fail ledger와 별개이다.

최종 운영 정책:
- 개발 단계: info + warning + error
- 운영 단계: error + 핵심 warning만

주의:
- 민감정보는 logger에 직접 남기지 않는다.
- fail ledger와 logger는 서로 역할이 다르므로 둘을 혼용하지 않는다.

==================================================
21. 보안 및 민감정보 처리
==================================================

1) DB 접속정보, API 키, 인증 헤더, 쿠키 등은 코드에 하드코딩하지 않는다.
2) 별도 비밀 저장소 또는 환경변수를 통해 주입한다.
3) raw 및 fail 저장소는 최소 권한 접근 원칙을 적용한다.
4) logger 및 fail 기록에는 민감정보를 남기지 않거나 마스킹한다.
5) cookie, auth header 저장은 금지한다.
6) DB/코드 기준이 어긋나는 임시 하드코딩 금지
7) 모든 인코딩은 UTF-8을 사용한다.

==================================================
22. 구현 시 금지 규칙
==================================================

1) Stage 내부에서 if reason_code == ... 로 action 판단 금지
2) Exception class에 retry_count, severity 직접 보관 금지
3) global mutable state 금지
4) raw overwrite 금지
5) 코드 테이블 값 하드코딩 금지
6) 동일 로직의 반복 구현 금지
7) fail ledger와 logger 혼용 금지
8) JSONL 구조를 stage마다 임의 변경 금지
9) DB/코드 기준이 어긋나는 임시 하드코딩 금지

==================================================
23. 최종 구현 순서 권장안
==================================================

1) Enum 정의
2) Model 클래스 정의
3) Exception class 정의
4) Resolver 정의
5) CodeTableRepository / StoreRepository 등 repository 정의
6) Query constants 정의
7) Collector 구조 정의
8) Storage / PathBuilder / JsonlWriter 정의
9) Stage I/O 모델 정의
10) Stage 구현
11) Handler / Pipeline 연결
12) Metrics / Logging / Monitoring 연결
13) 테스트 작성
14) 운영 배포

==================================================
24. 테스트 최소 기준
==================================================

1) Stage 단위 테스트
2) reason_code → action 매핑 테스트
3) code table repository mocking 테스트
4) dedup key 생성 테스트
5) Hive path 생성 테스트
6) batch_id / run_attempt 재실행 테스트
7) shard 재실행 테스트
8) load idempotency 테스트
9) fail 재처리 회귀 테스트
10) warning 승격 테스트

==================================================
25. 최종 결론
==================================================

본 설계는 다음을 최종 확정한다.

- JSONL 중심 중간 산출물 구조
- Resolver 중심 정책 판단 구조
- Exception class 기반 실패 의미 정의
- Fail Ledger 기반 운영 기록 구조
- 코드 테이블 중심 정규화 및 적재 구조
- target.csv를 1차 seed로 사용하는 수집 구조
- source_pool 확장 가능 구조 유지
- 플랫폼별 Collector 분리
- Stage 독립 재실행
- shard 단위 재실행
- Stage 3 dedup key 생성 / Stage 4 최종 dedup 판정
- batch_id + run_attempt 구조
- reason_code Enum + Exception class 유지
- 운영진 승인 기반 reason_code / resolver 변경 프로세스
- 개발/운영 logger 정책 분리
- AWS 비용을 고려한 효율적 구현 원칙

이 문서는 구현 시 다른 방향으로 가지 않기 위한 최종 설계 약속 문서로 사용한다.

==================================================
25. 최종 결론 (수정)
==================================================

기존:
- Stage 기반 단일 파이프라인

변경:

crawl project
→ process project
→ save project

failcheck project
→ fail 데이터 기반 후속 판단

핵심:

- crawl/process/save = 처리
- failcheck = 판단
- Resolver = 정책 기준

기존 설계 원칙은 유지하고
실행 구조만 프로젝트 단위로 분리한다.

==================================================
26. Update / Refresh 처리 규칙 (신규)
==================================================

26.1 목적

기존에 DB에 적재된 store가 시간이 지나면서
메뉴, 가격, 영업시간, 리뷰 등의 정보가 변경될 수 있다.

이를 반영하기 위해 "재수집(Update / Refresh)" 기능을 정의한다.

핵심 목표:

1. 신규 수집과 업데이트 수집을 명확히 구분한다.
2. 실제 데이터 변경 여부를 기반으로 DB 반영을 제어한다.
3. 불필요한 DB write를 줄인다.
4. 업데이트 추적 가능성을 확보한다.

---

## 26.2 target_type 확장

Stage 0은 수집 대상에 대해 target_type을 반드시 명시해야 한다.

target_type:

* NEW: 신규 수집 대상
* UPDATE: 기존 적재 store 재수집 대상
* RETRY: 실패 후 재시도 대상

원칙:

* UPDATE 대상은 기존 store_id 또는 dedup_key를 기반으로 선정한다.
* UPDATE 대상 여부는 Stage 0에서만 결정한다.
* Stage 1~4는 target_type에 따라 로직을 변경하지 않는다.

---

## 26.3 Update 감지 기준 (핵심)

업데이트 여부는 Stage 3에서 판단한다.

판단 기준:

entity별 content_hash 비교

기본 판단 단위:

* store_content_hash
* menu_content_hash
* review_content_hash
* image_content_hash

최종 변경 판단과 Stage 4 갱신 범위 결정은 entity별 hash를 기준으로 한다.

[entity별 content_hash 대상 필드]

store:

* normalized_name
* normalized_address
* phone
* opening_hours
* canonical_url

menu:

* menu_name
* price
* description

review:

* review_count
* rating
* latest_review_at

image:

* image_url

[판단 로직]

entity별 content_hash == previous entity별 content_hash → 해당 entity 변경 없음
entity별 content_hash != previous entity별 content_hash → 해당 entity 변경 있음

is_changed는 store_changed, menu_changed, review_changed, image_changed 중
하나라도 true인 경우 true로 본다.

---

## 26.4 Stage 역할 제한 (중요)

Stage는 다음까지만 수행한다.

* entity별 content_hash 생성
* previous entity별 content_hash 조회
* is_changed 판단
* changed_fields 생성

금지:

* 업데이트 여부에 따른 정책 결정
* skip / 강제 update 판단
* alert 판단

정책 판단은 failcheck / Resolver에서만 수행한다.

---

## 26.5 Stage 4 Load 규칙

[변경 발생 (is_changed = true)]

* 변경된 entity만 upsert 수행
* 변경된 entity별 content_hash 갱신
* last_updated_at 갱신
* update_detected_at 기록

[변경 없음 (is_changed = false)]

* 본문 데이터 수정 금지
* last_checked_at만 갱신

목적:

1. 실제 변경과 단순 확인을 구분한다.
2. 업데이트 주기 관리 가능
3. 불필요한 write 최소화

---

## 26.6 추적 필드 정의

다음 필드는 필수적으로 관리한다.

* store_content_hash
* menu_content_hash
* review_content_hash
* image_content_hash
* previous_store_content_hash
* previous_menu_content_hash
* previous_review_content_hash
* previous_image_content_hash
* store_changed
* menu_changed
* review_changed
* image_changed
* is_changed
* changed_fields
* last_checked_at
* last_updated_at
* update_detected_at

필수 판단 기준은 entity별 hash이다.

현재 스키마 호환 모드에서는 위 필드 중 DB에 존재하지 않는 필드를
물리 컬럼으로 요구하지 않는다.

* `last_checked_at`은 `MAX(crawling.created_at)`으로 계산한다.
* `*_content_hash`와 `previous_*_content_hash`는 Stage 산출물 또는 Repository 응답의 논리 필드로 관리한다.
* 물리 저장이 필요한 경우에는 향후 스키마 확장 모드에서 컬럼을 추가한다.

---

## 26.7 변경 필드 기록 정책

changed_fields는 전체 diff가 아니라
핵심 필드 기준으로만 기록한다.

예시:

{
"changed_fields": {
"menu": true,
"price": true,
"opening_hours": false
}
}

---

## 26.8 Dedup / Update 관계

* Dedup 판정은 기존 규칙을 그대로 따른다.
* Update는 dedup_key 또는 store_id 기준으로 수행한다.
* Dedup 충돌 시 update 처리보다 우선한다.

---

## 26.8.1 현재 스키마 호환 모드

현재 `database/init.sql` 스키마에 `dedup_key`, `canonical_url`, `*_content_hash`,
물리 `last_checked_at` 컬럼이 없는 경우에는 현재 스키마 호환 모드를 사용한다.

현재 스키마 호환 모드의 원칙:

* 신규 컬럼을 전제로 하지 않는다.
* `last_checked_at`은 DB 컬럼이 아니라 논리 필드로 본다.
* 논리 `last_checked_at`은 해당 store/map에 연결된 `crawling.created_at`의 최신값으로 계산한다.
* UPDATE 대상 선정은 최근 저장일 기준으로 수행한다.
* 중복/동일성 판단은 현재 스키마에 존재하는 컬럼만 사용한다.
* 이름/주소 변경 가능성은 별도 가정으로 처리하지 않는다.
* PostgreSQL `MERGE` 또는 동등한 upsert 로직을 사용해 insert/update 정책을 명시한다.

현재 스키마 호환 모드의 기본 매칭 기준:

* maps: `name`, `category_cd`, `address_cd`, `address_detail`
* shop: `map_id`, `shop_cd`
* menu: `shop_id`, `name`
* images: `table_cd`, `table_id`, `image_url`
* crawling: `article_url`, `map_id`, 필요 시 `title`/`content`

`dedup_key`, `canonical_url`, `*_content_hash`, 물리 `last_checked_at`은
향후 스키마 확장 모드의 필드로 둔다.

---

## 26.9 Fail 처리

UPDATE 대상도 일반 실패 처리 규칙을 그대로 따른다.

* 실패 시 fail ledger 기록
* retry / reprocess 판단은 failcheck에서 수행

---

## 26.10 확장 가능 포인트 (운영)

향후 failcheck / Resolver에서 다음 정책 확장이 가능하다.

* 오래 업데이트 안 된 store 자동 refresh
* 특정 변경 (가격 급등 등) alert
* 변경 없음 반복 시 sampling 감소

==================================================
27. previous content_hash 조회 구조 설계 (신규)
=======================================

27.1 목적

Stage 3에서 entity별 content_hash를 생성하여 변경 여부를 판단하기 위해서는
기존 DB에 저장된 previous entity별 content_hash를 조회해야 한다.

단, 다음 설계 원칙을 반드시 준수해야 한다.

* Stage는 데이터 처리만 담당한다.
* Stage는 DB 구조를 직접 알면 안 된다.
* SQL은 Repository 계층을 통해서만 접근한다.

따라서 previous content_hash 조회는 별도의 Repository 계층을 통해 수행한다.

---

## 27.2 SnapshotRepository 도입

기존 StoreRepository와 별도로
previous content_hash 조회 전용 Repository를 정의한다.

역할:

* 현재 DB 상태의 snapshot을 조회한다.
* entity별 content_hash 기반 비교를 지원한다.
* Stage 3이 DB 구조를 몰라도 되도록 한다.

명칭:

SnapshotRepository

---

## 27.3 SnapshotRepository 인터페이스

get_store_snapshot(dedup_key) → {
store_id,
store_content_hash,
menu_content_hash,
review_content_hash,
image_content_hash,
last_updated_at,
last_checked_at
}

get_menu_snapshot(store_id) → {
menu_content_hash
}

get_review_snapshot(store_id) → {
review_content_hash
}

get_image_snapshot(store_id) → {
image_content_hash
}

단건 조회와 bulk 조회 모두 동일한 hash 필드 구조를 반환해야 한다.
단일 content_hash만 반환하는 구조는 사용하지 않는다.

---

## 27.4 조회 기준 (Dedup 정책 재사용)

Snapshot 조회 시 기준은 기존 Dedup 정책을 그대로 따른다.

우선순위:

1. store_id (존재 시 최우선)
2. canonical_url
3. normalized_name + normalized_address

원칙:

* 새로운 조회 기준을 만들지 않는다.
* Dedup 기준과 반드시 동일해야 한다.

---

## 27.5 Stage 3 적용 흐름

Stage 3의 처리 순서는 다음과 같다.

1. normalized 데이터 생성
2. dedup_key 생성
3. SnapshotRepository 조회
4. previous entity별 content_hash 획득
5. entity별 content_hash 생성
6. entity별 content_hash 비교
7. entity별 변경 여부 및 is_changed 판단
8. changed_fields 생성

Stage는 판단 결과만 생성하며,
정책 결정은 수행하지 않는다.

---

## 27.6 Bulk 조회 전략 (성능)

Stage 3에서 개별 건마다 DB 조회를 수행하면
성능 및 비용 문제가 발생한다.

따라서 bulk 조회 방식을 사용한다.

방식:

1. Stage 시작 시 dedup_key 리스트 추출
2. SnapshotRepository.bulk_get(dedup_keys) 호출
3. 결과를 in-memory dict로 구성
4. 이후 모든 조회는 메모리에서 수행

예시:

{
"dedup_key_1": snapshot,
"dedup_key_2": snapshot
}

---

## 27.7 Cache 원칙

Snapshot 조회 결과는 handler 실행 범위 내에서만 캐시한다.

원칙:

* handler scope cache 허용
* global cache 금지
* TTL 없음
* 실행 종료 시 폐기

이는 기존 Design.md의 cache 정책을 그대로 따른다.

---

## 27.8 금지 사항

다음 구현은 금지한다.

* Stage 내부에서 직접 SQL 실행
* Stage 내부에서 DB schema 의존
* dedup 기준과 다른 조회 기준 사용
* record 단위 반복 DB 조회 (N+1 문제)
* global cache 사용

---

## 27.9 최종 정리

Stage 3은 DB를 직접 조회하지 않는다.
Stage 3은 SnapshotRepository를 통해 간접적으로 snapshot을 조회한다.

이를 통해 다음을 달성한다.

1. Stage 책임 분리 유지
2. DB 구조 의존성 제거
3. 성능 최적화 (bulk 조회)
4. 확장성 확보 (menu/review/image 포함)

==================================================
27. previous content_hash 조회 구조 설계 (신규) END
===========================================

==================================================
28. Stage 4 Upsert 전략 (신규)
==========================

28.1 목적

Stage 4 Save는 Stage 3에서 생성한 is_changed 결과를 기준으로
기존 DB 데이터를 안전하게 갱신한다.

핵심 목표:

1. 변경된 데이터만 DB에 반영한다.
2. 크롤링 누락으로 기존 데이터를 파괴하지 않는다.
3. insert / update를 멱등성 있게 처리한다.
4. store, menu, review, image의 성격에 맞는 갱신 방식을 분리한다.

---

## 28.1.1 현재 스키마 호환 Upsert 전략

현재 스키마 호환 모드에서는 Stage 4가 신규 컬럼을 요구하지 않는다.

원칙:

* Store/Map 적재는 현재 스키마의 실제 컬럼 기준으로 `MERGE` 또는 동등한 upsert를 수행한다.
* `maps`는 `name`, `category_cd`, `address_cd`, `address_detail` 조합을 기준으로 매칭한다.
* `shop`은 `map_id`, `shop_cd` 조합을 기준으로 매칭한다.
* `menu`는 `shop_id`, `name` 조합을 기준으로 매칭한다.
* `images`는 `table_cd`, `table_id`, `image_url` 조합을 기준으로 중복 저장을 방지한다.
* `table_cd`는 이미지가 연결된 원천 테이블의 `codeT` 테이블 코드이다.
* `table_id`는 해당 원천 테이블의 실제 PK이다.
* 현재 스키마에 없는 `dedup_key`, `canonical_url`, `*_content_hash`, 물리 `last_checked_at` 컬럼은 사용하지 않는다.

이 모드에서 `last_checked_at`은 `crawling.created_at`의 최신값으로 계산되는 논리 값이다.
따라서 Stage 4가 확인 이력을 남겨야 하는 경우 `crawling` row를 기록하고,
Stage 0/Repository는 `MAX(crawling.created_at)`을 `last_checked_at`으로 해석한다.

---

## 28.2 Store Upsert 원칙

Store는 non-null partial update 방식을 사용한다.

원칙:

* 신규 normalized 값이 null이 아닌 필드만 갱신한다.
* 신규 값이 null이면 기존 DB 값을 유지한다.
* 크롤링 누락값으로 기존 유효값을 덮어쓰지 않는다.
* store_id가 있으면 store_id 기준으로 갱신한다.
* store_id가 없으면 dedup_key 기준으로 기존 store를 찾는다.

적용 필드 예시:

* normalized_name
* normalized_address
* phone
* opening_hours
* canonical_url
* store_content_hash
* last_checked_at
* last_updated_at
* update_detected_at

---

## 28.3 Menu Upsert 원칙

Menu는 menu_name 기준 upsert 방식을 사용한다.

원칙:

* 동일 store_id + menu_name 조합이 있으면 기존 menu를 갱신한다.
* 신규 menu_name이면 새 menu로 추가한다.
* 이번 수집 결과에 없는 기존 menu는 삭제하지 않고 missing_count를 증가시킨다.
* missing_count가 threshold에 도달한 경우에만 inactive 처리한다.
* 가격 변경은 기존 menu row 갱신으로 처리한다.
* 메뉴 이력 보존을 위해 hard delete는 금지한다.

상태 예시:

* active = true
* active = false

inactive 처리 의미:

* 실제 삭제 확정이 아니라,
  여러 번의 수집에서 연속 미검출된 메뉴라는 운영 상태로 해석한다.
* inactive 처리의 최종 기준은 30장 Menu Inactive 처리 기준을 따른다.

현재 스키마 호환 모드:

* `menu` 테이블에 `active`, `missing_count`, `last_seen_at`, `inactivated_at`, `inactive_reason` 컬럼이 없는 경우 missing_count 증가 및 inactive 처리를 수행하지 않는다.
* 이번 수집에서 검출된 menu만 upsert(WHERE NOT EXISTS)하며, 누락 판단은 스키마 확장 모드의 책임으로 유예한다.
* 30장의 상태 전이 규칙은 스키마 확장 모드에서 구현한다.

---

## 28.4 Review Upsert 원칙

Review는 source_review_id 또는 review_hash 기준 append-only 방식을 사용한다.

원칙:

* 기존 review는 삭제하지 않는다.
* source_review_id가 있으면 이를 우선 중복 기준으로 사용한다.
* source_review_id가 없으면 review_hash를 사용한다.
* 이미 존재하는 review는 중복 저장하지 않는다.
* 새 review만 추가한다.

주의:

* 리뷰 수정 여부는 현재 단계에서 별도 갱신 대상으로 보지 않는다.
* 리뷰 삭제 여부도 현재 단계에서 판단하지 않는다.
* 리뷰는 이력성 데이터로 보고 append-only를 기본으로 한다.

---

## 28.5 Image Upsert 원칙

Image는 image_url hash 기준 upsert 방식을 사용한다.

원칙:

* image_url을 정규화한 뒤 hash를 생성한다.
* 동일 image_url hash가 있으면 중복 저장하지 않는다.
* 신규 image_url hash면 새 image로 추가한다.
* 기존 image는 삭제하지 않는다.
* 이미지 삭제 여부는 현재 단계에서 판단하지 않는다.

주의:

* 플랫폼 수집 누락 가능성이 있으므로
  image는 menu보다 더 보수적으로 처리한다.
* missing image inactive 처리는 초기 기본 정책으로 사용하지 않는다.

---

## 28.6 변경 없음 처리

is_changed = false인 경우 Stage 4는 본문 데이터를 수정하지 않는다.

수행:

* last_checked_at만 갱신한다.

현재 스키마 호환 모드:

* 물리 `last_checked_at` 컬럼을 갱신하지 않는다.
* 확인 이력이 필요한 경우 `crawling`에 확인 row를 남긴다.
* 이후 `last_checked_at`은 해당 store/map의 `MAX(crawling.created_at)`으로 계산한다.
* 본문 데이터가 변경되지 않았다는 원칙은 유지한다.

금지:

* store 본문 필드 갱신
* menu 갱신
* review 추가
* image 추가
* entity별 content_hash 변경

목적:

1. 단순 확인과 실제 변경을 분리한다.
2. 불필요한 DB write를 줄인다.
3. 최근 확인 시점을 추적한다.

---

## 28.7 변경 발생 처리

is_changed = true인 경우 Stage 4는 entity별 변경 여부에 따라 필요한 부분만 처리한다.

1. store_changed = true이면 store non-null partial update
2. menu_changed = true이면 menu upsert 및 missing_count / inactive 처리
3. review_changed = true이면 review append-only 추가
4. image_changed = true이면 image hash 기준 upsert
5. 변경된 entity별 content_hash 갱신
6. last_updated_at 갱신
7. update_detected_at 기록
8. last_checked_at 갱신

is_changed = true라도 특정 entity의 *_changed 값이 false이면
해당 entity의 본문 데이터는 수정하지 않는다.

원칙:

* store 갱신 실패 시 해당 store 전체를 fail 처리한다.
* menu/review/image 일부 실패는 partial_failure로 기록한다.
* fail ledger는 비즈니스 트랜잭션과 분리한다.

---

## 28.8 삭제 처리 원칙

크롤링 기반 데이터에서는 삭제보다 보수적 비활성화를 우선한다.

원칙:

* store hard delete 금지
* menu hard delete 금지
* review hard delete 금지
* image hard delete 금지

menu:

* 이번 수집에서 누락된 기존 menu는 missing_count 증가 대상
* inactive 전환은 30장의 threshold 기준을 따른다

review:

* 삭제 판단하지 않음

image:

* 삭제 판단하지 않음

이유:

* 크롤링 누락과 실제 삭제를 구분하기 어렵기 때문이다.
* 잘못된 삭제는 데이터 손실로 이어진다.

---

## 28.9 Transaction 경계

기존 Load / Transaction 경계 원칙을 유지한다.

* store: 1 트랜잭션
* menu: 별도 트랜잭션
* review: 별도 트랜잭션
* image: 별도 트랜잭션
* fail ledger: 비즈니스 트랜잭션과 분리

운영 의미:

* store 적재 실패 → 해당 store 전체 실패
* store 성공 후 menu/review/image 일부 실패 → partial_failure 기록
* 실패한 종속 엔티티는 fail ledger에 별도 기록 후 failcheck에서 후속 판단

---

## 28.10 금지 사항

다음 구현은 금지한다.

* 변경 없음인데 본문 데이터 갱신
* null 값으로 기존 유효값 overwrite
* menu 전체 삭제 후 재삽입
* review 전체 삭제 후 재삽입
* image 전체 삭제 후 재삽입
* Stage 내부에서 upsert 정책 임의 변경
* Stage 내부에서 retry/reprocess/alert 판단
* fail ledger와 DB 비즈니스 트랜잭션 혼합

---

## 28.11 최종 정리

Stage 4 Upsert 최종 방식은 다음과 같다.

Store:

* non-null partial update

Menu:

* store_id + menu_name 기준 upsert
* 누락 메뉴는 missing_count 증가 후 threshold 충족 시 inactive 처리
* hard delete 금지

Review:

* source_review_id 또는 review_hash 기준 append-only
* 기존 review 삭제 금지

Image:

* image_url hash 기준 upsert
* 기존 image 삭제 금지

변경 없음:

* 본문 수정 금지
* last_checked_at만 갱신
* 현재 스키마 호환 모드에서는 확인 이력 `crawling` row를 남기고 `MAX(crawling.created_at)`을 논리 `last_checked_at`으로 사용

변경 있음:

* 필요한 엔티티만 안전하게 갱신
* 변경된 entity별 content_hash / last_updated_at / update_detected_at / last_checked_at 갱신
* 현재 스키마 호환 모드에서는 현재 스키마에 존재하는 컬럼만 갱신하고, hash/timestamp 물리 컬럼 갱신은 생략

==================================================
28. Stage 4 Upsert 전략 (신규) END
==============================

==================================================
29. entity별 content_hash 생성 규칙 (신규)
===========================

29.1 목적

Stage 3에서 생성되는 entity별 content_hash는
데이터 변경 여부를 판단하는 핵심 기준이다.

동일한 데이터는 항상 동일한 hash가 생성되어야 하며,
미세한 표현 차이로 인해 다른 hash가 생성되는 것을 방지해야 한다.

따라서 entity별 content_hash는 재현성과 안정성을 보장하는 방식으로 생성해야 한다.

---

## 29.2 생성 방식 (확정)

entity별 content_hash는 canonical JSON + SHA256 방식으로 생성한다.

원칙:

* 정규화된 데이터를 canonical JSON 형태로 직렬화한다.
* 직렬화된 문자열에 SHA256 해시를 적용한다.

이 방식은 다음을 보장한다.

1. 동일 데이터 → 동일 hash
2. 필드 순서 변화에 영향 없음
3. 테스트 및 검증 용이
4. Stage 3 변경 감지 기준으로 안정적

---

## 29.3 canonical JSON 생성 규칙

entity별 content_hash 생성 전에 반드시 다음 정규화 과정을 거친다.

1. hash 대상 필드만 추출한다.

2. null family 통일

* None
* ""
* " "
* NaN

→ 모두 동일한 null 값으로 처리한다.

3. 문자열 처리

* 앞뒤 공백 제거 (trim)
* 불필요한 공백 표준화

4. 리스트(List) 처리

* 순서에 의미가 없는 경우 정렬 후 사용
* 정렬 기준은 명시적으로 정의한다 (예: menu_name 기준)

5. dict / object 처리

* key 기준 정렬한다

6. JSON 직렬화 규칙

* key 순서 고정
* 공백 없는 compact JSON 사용
* encoding: UTF-8

7. 최종 문자열 생성 후 SHA256 적용

---

## 29.4 적용 대상 데이터

entity별 content_hash는 다음 데이터를 포함한다.

store:

* normalized_name
* normalized_address
* phone
* opening_hours
* canonical_url

menu:

* menu_name
* price
* description

review:

* review_count
* rating
* latest_review_at

image:

* image_url

---

## 29.5 생성 위치

entity별 content_hash는 Stage 3 (Validation & Normalization)에서 생성한다.
기본 생성 단위는 entity별 hash이다.

Stage 3 산출물에 반드시 포함한다.

필수 필드:

* store_content_hash
* menu_content_hash
* review_content_hash
* image_content_hash
* previous_store_content_hash
* previous_menu_content_hash
* previous_review_content_hash
* previous_image_content_hash
* store_changed
* menu_changed
* review_changed
* image_changed
* is_changed
* changed_fields

---

## 29.6 버전 관리 필드

entity별 content_hash 생성 규칙 변경 가능성을 고려하여
다음 필드를 함께 기록한다.

* hash_version
* hash_fields_version

의미:

hash_version:

* hash 알고리즘 또는 생성 방식 변경 시 증가

hash_fields_version:

* hash 대상 필드 구조 변경 시 증가

---

## 29.7 금지 사항

다음 방식은 금지한다.

* 단순 문자열 concat 기반 hash 생성
* 필드 순서에 의존하는 hash 생성
* null 값을 그대로 사용하는 방식
* 리스트 정렬 없이 hash 생성
* JSON 직렬화 규칙이 고정되지 않은 방식

---

## 29.8 최종 정리

entity별 content_hash는 canonical JSON + SHA256 방식으로 생성한다.

생성 전 데이터는 다음을 보장해야 한다.

* null family 정규화
* 문자열 trim
* 리스트 정렬
* dict key 정렬

추가로 다음 필드를 함께 기록한다.

* hash_version
* hash_fields_version

이를 통해 entity별 content_hash는
변경 감지의 신뢰 가능한 기준으로 사용된다.

최종 판단 기준은 31장의 entity별 content_hash 저장 구조를 따른다.

==================================================
29. entity별 content_hash 생성 규칙 (신규) END
===============================


==================================================
30. Menu Inactive 처리 기준 (신규)
============================

30.1 목적

크롤링 기반 데이터에서는
"이번 수집 결과에 존재하지 않는다"는 사실만으로
해당 데이터가 실제로 삭제되었다고 판단할 수 없다.

따라서 menu 데이터는 즉시 삭제하거나 비활성화하지 않고,
여러 번의 검증을 통해 안정적으로 상태를 변경해야 한다.

핵심 목표:

1. 크롤링 누락으로 인한 데이터 손상을 방지한다.
2. 실제 삭제와 수집 실패를 구분한다.
3. menu 상태 변경을 안정적으로 수행한다.

---

## 30.2 기본 원칙

* menu는 hard delete 하지 않는다.
* 단일 수집 결과만으로 inactive 처리하지 않는다.
* 반복 검증을 통해 inactive 여부를 판단한다.

---

## 30.3 inactive 처리 기준 (확정)

menu는 "N회 연속 미검출" 기준으로 inactive 처리한다.

확정 기준:

* threshold = 3

즉,

동일 store_id + menu_name 기준으로
3회 연속 수집에서 검출되지 않은 경우에만 inactive 처리한다.

---

## 30.4 상태 전이 규칙

[메뉴가 이번 수집에서 발견된 경우]

* active = true
* missing_count = 0
* last_seen_at 갱신

[메뉴가 이번 수집에서 발견되지 않은 경우]

* missing_count += 1

missing_count < 3:

* active 상태 유지

missing_count >= 3:

* active = false
* inactivated_at 기록
* inactive_reason 기록

---

## 30.5 복구 규칙

inactive 상태의 menu가 이후 수집에서 다시 발견되면:

* active = true
* missing_count = 0
* last_seen_at 갱신
* inactivated_at 유지 또는 정책에 따라 초기화 가능

---

## 30.6 관리 필드 정의

menu 엔티티는 다음 필드를 반드시 포함해야 한다.

* active (boolean)
* missing_count (int)
* last_seen_at (datetime)
* inactivated_at (datetime)
* inactive_reason (string)

---

## 30.7 inactive_reason 정의

기본 값:

* "MISSING_3_CONSECUTIVE_REFRESH"

추후 확장 가능:

* "MANUAL_INACTIVE"
* "INVALID_MENU"
* 기타 운영 정책 기반 값

---

## 30.8 금지 사항

다음 구현은 금지한다.

* 단일 수집 결과로 inactive 처리
* menu hard delete
* missing_count 없이 상태 변경
* 크롤링 실패를 menu 삭제로 해석
* inactive 상태를 외부 정책 없이 자동 삭제로 연결

---

## 30.9 최종 정리

현재 스키마 호환 모드:

* `menu` 테이블에 30.6의 관리 필드(`active`, `missing_count`, `last_seen_at`, `inactivated_at`, `inactive_reason`)가 없는 경우 본 장의 처리를 전면 생략한다.
* 현재 스키마에서는 수집된 menu를 `WHERE NOT EXISTS` 기반 INSERT로만 처리한다.
* missing_count 기반 inactive 판단 및 상태 전이는 스키마 확장 모드에서 구현한다.

---

menu는 단순 누락을 삭제로 판단하지 않는다.

동일 store_id + menu_name 기준으로
3회 연속 미검출된 경우에만 inactive 처리한다.

이를 통해 다음을 보장한다.

1. 크롤링 노이즈 방어
2. 데이터 손상 방지
3. 안정적인 상태 관리

==================================================
30. Menu Inactive 처리 기준 (신규) END
================================

==================================================
31. entity별 content_hash 저장 구조 (신규)
===========================

31.1 목적

entity별 content_hash는 Stage 3의 변경 감지와 Stage 4의 upsert 판단에 사용되는 핵심 기준이다.

따라서 entity별 content_hash는 단일 값으로 관리하지 않고,
store / menu / review / image 단위로 분리하여 저장한다.

핵심 목표:

1. 변경 범위를 정확히 구분한다.
2. 불필요한 전체 update를 방지한다.
3. SnapshotRepository 조회 구조를 명확히 한다.
4. Stage 4에서 부분 업데이트가 가능하도록 한다.

---

## 31.2 저장 방식 (확정)

entity별 content_hash는 entity별로 분리하여 저장한다.

관리 필드:

* store_content_hash
* menu_content_hash
* review_content_hash
* image_content_hash

원칙:

* store는 store row에 store_content_hash를 저장한다.
* menu는 store 단위 aggregate hash로 관리한다.
* review는 store 단위 aggregate hash로 관리한다.
* image는 store 단위 aggregate hash로 관리한다.

현재 스키마 호환 모드:

* `store_content_hash`, `menu_content_hash`, `review_content_hash`, `image_content_hash` 컬럼을 요구하지 않는다.
* hash는 Stage 3 산출물과 변경 판단용 논리 값으로 유지한다.
* previous hash 조회가 불가능한 경우에는 현재 스키마의 최근 저장일과 저장된 crawling 이력을 기준으로 재확인 대상을 판단한다.
* hash 물리 저장은 향후 스키마 확장 모드의 책임으로 둔다.

---

## 31.3 Aggregate Hash 정의

menu / review / image는 개별 row 단위 hash보다
store 단위 집합 상태를 기준으로 hash를 생성한다.

menu_content_hash:

* 해당 store의 menu list를 기준으로 생성한다.
* menu list는 정렬 후 canonical JSON + SHA256 방식으로 hash 처리한다.

review_content_hash:

* 해당 store의 review summary를 기준으로 생성한다.
* review_count, rating, latest_review_at 등을 포함한다.

image_content_hash:

* 해당 store의 image_url list를 기준으로 생성한다.
* image_url list는 정렬 후 canonical JSON + SHA256 방식으로 hash 처리한다.

---

## 31.4 Stage 3 생성 필드

Stage 3은 다음 hash를 생성한다.

* store_content_hash
* menu_content_hash
* review_content_hash
* image_content_hash

전체 변경 판단은 entity별 변경 여부를 조합한 is_changed로 수행한다.

---

## 31.5 SnapshotRepository 반환 구조

SnapshotRepository는 기존 단일 content_hash가 아니라
entity별 hash를 반환해야 한다.

반환 구조 예시:

{
"store_id": "store_123",
"store_content_hash": "hash_store",
"menu_content_hash": "hash_menu",
"review_content_hash": "hash_review",
"image_content_hash": "hash_image",
"last_updated_at": "2026-04-25T10:00:00",
"last_checked_at": "2026-04-27T10:00:00"
}

---

## 31.6 변경 판단 방식

Stage 3은 SnapshotRepository에서 조회한 기존 hash와
새로 생성한 hash를 비교하여 entity별 변경 여부를 판단한다.

판단 필드:

* store_changed
* menu_changed
* review_changed
* image_changed
* is_changed

판단 로직:

store_changed:

* store_content_hash != previous_store_content_hash

menu_changed:

* menu_content_hash != previous_menu_content_hash

review_changed:

* review_content_hash != previous_review_content_hash

image_changed:

* image_content_hash != previous_image_content_hash

is_changed:

* store_changed
* 또는 menu_changed
* 또는 review_changed
* 또는 image_changed 중 하나라도 true인 경우 true

---

## 31.7 Stage 4 적용 방식

Stage 4는 entity별 변경 여부에 따라 필요한 부분만 갱신한다.

적용 기준:

store_changed = true:

* store non-null partial update 수행

menu_changed = true:

* menu upsert 수행
* missing menu count 갱신
* threshold 충족 시 inactive 처리

review_changed = true:

* source_review_id 또는 review_hash 기준 append-only 추가

image_changed = true:

* image_url hash 기준 upsert

is_changed = false:

* 본문 데이터 수정 금지
* last_checked_at만 갱신

---

## 31.8 previous hash 필드

Stage 3 산출물에는 이전 hash도 함께 포함한다.

필수 필드:

* previous_store_content_hash
* previous_menu_content_hash
* previous_review_content_hash
* previous_image_content_hash

목적:

1. 변경 판단 근거를 추적한다.
2. 디버깅과 회귀 테스트에 활용한다.
3. fail ledger 기록 시 원인 분석을 쉽게 한다.

---

## 31.9 버전 관리

entity별 hash에도 동일한 버전 관리 원칙을 적용한다.

필수 필드:

* hash_version
* hash_fields_version

의미:

hash_version:

* hash 생성 알고리즘 또는 canonical JSON 생성 방식 변경 시 증가

hash_fields_version:

* hash 대상 필드 구성이 변경될 때 증가

---

## 31.10 금지 사항

다음 구현은 금지한다.

* 단일 content_hash 하나만으로 모든 변경 판단
* menu/review/image 변경을 store 변경으로만 처리
* entity별 previous hash 없이 변경 판단
* Stage 4에서 변경 여부를 다시 임의 판단
* hash 저장 위치를 Stage마다 다르게 해석
* 개별 row 삭제를 hash 변경의 기본 후속 조치로 연결

---

## 31.11 최종 정리

entity별 content_hash는 entity별로 분리하여 저장한다.

최종 관리 단위:

Store:

* store_content_hash

Menu:

* menu_content_hash

Review:

* review_content_hash

Image:

* image_content_hash

Stage 3은 entity별 hash를 생성하고,
SnapshotRepository를 통해 기존 hash와 비교한다.

Stage 4는 entity별 변경 여부에 따라
필요한 부분만 안전하게 갱신한다.

이를 통해 다음을 보장한다.

1. 변경 감지 정확도 향상
2. 불필요한 전체 update 방지
3. SnapshotRepository 구조 명확화
4. Store/Menu/Review/Image별 안전한 upsert 가능

==================================================
31. entity별 content_hash 저장 구조 (신규) END
===============================

==================================================
32. Update 주기 정책 (신규)
=====================

32.1 목적

이미 DB에 적재된 store는 시간이 지남에 따라
메뉴, 가격, 영업시간, 리뷰 등의 정보가 변경될 수 있다.

이를 반영하기 위해 모든 store를 일정 주기로 재수집하는
Update 주기 정책을 정의한다.

핵심 목표:

1. 모든 store를 일정 주기로 최신 상태로 유지한다.
2. 운영 정책을 단순하게 유지한다.
3. AWS 비용과 처리량을 고려한 현실적인 업데이트를 수행한다.

---

## 32.2 정책 방식 (확정)

Update 주기 정책은 "전체 store 일괄 주기 업데이트 방식"을 사용한다.

원칙:

* 모든 store는 동일한 refresh 주기를 가진다.
* 특정 store만 별도로 우선 처리하지 않는다.
* Stage 0에서 UPDATE 대상을 선정한다.

---

## 32.3 Update 대상 선정 기준

Stage 0은 다음 기준으로 UPDATE 대상을 선정한다.

기본 기준:

* last_checked_at이 refresh_interval_days 이상 경과한 store

즉:

현재 시각 - last_checked_at >= refresh_interval_days

→ UPDATE 대상

현재 스키마 호환 모드:

* `last_checked_at`은 물리 컬럼이 아니라 `crawling.created_at` 기반 논리 값이다.
* store/map별 `MAX(crawling.created_at)`을 최근 저장일로 계산한다.
* 최근 저장일이 없거나, 최근 저장일이 `refresh_interval_days` 이상 지난 경우 UPDATE 대상으로 본다.
* 재수집 URL은 기존에 저장된 `crawling.article_url`을 사용한다.
* 동일성 판단과 대상 추출은 현재 스키마에 있는 `maps`, `shop`, `crawling` 컬럼만 사용한다.

---

## 32.4 주기 설정

기본 설정:

* refresh_interval_days = 30

의미:

* 모든 store는 최소 30일에 한 번 이상 재수집된다.

---

## 32.5 Daily Update Quota

모든 store를 한 번에 처리하지 않기 위해
일별 처리량 제한(quota)을 둔다.

원칙:

* category_cd별로 update_daily_quota를 설정한다.
* quota를 초과하는 경우 일부 store만 선택한다.

선정 방식:

* last_checked_at이 오래된 순으로 정렬
* 오래된 store부터 quota만큼 선택

현재 스키마 호환 모드에서는 `last_checked_at` 정렬을
`MAX(crawling.created_at)` 오름차순 정렬로 대체한다.

---

## 32.6 Stage 0 적용 방식

Stage 0은 기존 Daily Target Selection 원칙을 유지하면서
UPDATE 대상을 함께 구성한다.

전체 우선순위:

1. RETRY 대상
2. UPDATE 대상
3. NEW 대상

원칙:

* RETRY는 기존 6.2의 "retry 대상 우선 포함" 원칙을 유지한다.
* UPDATE는 update_daily_quota 범위 안에서만 포함한다.
* NEW는 남은 daily target quota를 채우는 보충 대상이다.
* target_type은 Stage 0에서만 결정한다.

UPDATE 대상 구성 순서:

1. last_checked_at 기준으로 UPDATE 후보 추출
2. refresh_interval_days 이상 경과한 store 필터링
3. last_checked_at 기준 오름차순 정렬
4. category_cd별 quota 적용
5. target_type = UPDATE 설정

---

## 32.7 target_type 및 이유 코드

UPDATE 대상은 다음 값을 가진다.

target_type:

* UPDATE

update_reason:

* SCHEDULED_REFRESH

의미:

* 주기 기반 자동 재수집 대상

---

## 32.8 예외 처리

다음 상황에서는 UPDATE 대상에서 제외될 수 있다.

* 최근 retry / reprocess 수행 중인 store
* fail 상태로 별도 처리 중인 store

단, 예외 처리 기준은 Stage에서 판단하지 않는다.
failcheck / Resolver 정책에 따른다.

---

## 32.9 금지 사항

다음 구현은 금지한다.

* Stage 내부에서 임의로 update 대상 선정
* 특정 store만 하드코딩하여 우선 처리
* last_checked_at을 무시한 무작위 업데이트
* quota 없이 전체 store를 한 번에 재수집
* 정책 없이 수동 업데이트 수행

---

## 32.10 최종 정리

Update 주기 정책은 전체 store 일괄 주기 업데이트 방식을 사용한다.

핵심 기준:

* refresh_interval_days = 30
* last_checked_at 기준으로 UPDATE 대상 선정
* 오래된 store부터 우선 처리
* category_cd별 daily quota 적용

Stage 0은 위 기준을 기반으로
기존 6.2 원칙과 함께 RETRY / UPDATE / NEW 대상을 구성한다.

이를 통해 다음을 보장한다.

1. 전체 데이터의 주기적 최신화
2. 단순하고 일관된 운영 정책
3. 비용과 처리량을 고려한 안정적인 운영

==================================================
32. Update 주기 정책 (신규) END
=========================

==================================================
33. partial_failure 세부 처리 규칙 (신규)
=================================

33.1 목적

크롤링 기반 ETL 구조에서는
store, menu, review, image가 서로 다른 단위로 처리되기 때문에
일부만 실패하는 상황(partial_failure)이 발생할 수 있다.

이를 안전하게 처리하기 위해
entity 단위 partial_failure 처리 규칙을 정의한다.

핵심 목표:

1. store 단위 데이터 일관성을 유지한다.
2. 실패한 entity만 재처리 가능하도록 한다.
3. 불필요한 전체 rollback을 방지한다.
4. failcheck와 자연스럽게 연동한다.

---

## 33.2 기본 원칙

* store는 핵심 엔티티이다.
* menu / review / image는 종속 엔티티이다.
* store 성공 여부가 전체 처리 기준이 된다.
* 부분 실패는 허용한다.
* 실패는 fail ledger로 기록한다.

---

## 33.3 처리 기준 (확정)

[Case 1: store 실패]

* store insert/update 실패
* 해당 store 전체를 fail로 처리한다.
* menu / review / image 처리 금지
* fail ledger에 store 실패 기록
* 후속 처리는 failcheck에서 결정

[Case 2: store 성공 + 일부 entity 실패]

* store는 정상 commit 유지
* 실패한 entity(menu/review/image)만 fail ledger 기록
* batch 결과는 partial_failure로 기록
* 성공한 entity는 그대로 유지

---

## 33.4 entity별 처리 규칙

store:

* 실패 시 전체 fail
* 성공 시 commit 유지

menu:

* 일부 menu 처리 실패 가능
* 실패한 menu만 fail ledger 기록
* 나머지 menu는 정상 반영

review:

* 일부 review 처리 실패 가능
* 실패한 review만 fail ledger 기록
* 나머지 review는 append-only 유지

image:

* 일부 image 처리 실패 가능
* 실패한 image만 fail ledger 기록
* 나머지 image는 정상 반영

---

## 33.5 retry / reprocess 범위

partial_failure 발생 시
재처리는 실패한 entity 단위로 수행한다.

원칙:

* store 전체 재처리 금지
* 성공한 entity 재처리 금지
* 실패한 entity만 retry/reprocess 대상으로 기록

예시:

* menu 실패 → menu만 재처리
* review 실패 → review만 재처리

---

## 33.6 fail ledger 기록 기준

fail ledger에는 다음 정보를 기록한다.

필수 필드:

* batch_id
* run_attempt
* stage
* entity_type (store/menu/review/image)
* entity_id
* reason_code
* retry_count
* created_at

추가 권장 필드:

* origin_batch_id
* target_type
* update_reason

---

## 33.7 batch 상태 정의

batch 단위 상태는 다음과 같이 정의한다.

* success:
  모든 entity 처리 성공

* partial_failure:
  store 성공 + 일부 entity 실패

* fail:
  store 실패

---

## 33.8 failcheck 연계

failcheck는 fail ledger를 기반으로
entity 단위 후속 처리를 수행한다.

가능한 action:

* retry
* reprocess
* drop
* alert
* warning
* manual_check

주의:

* Stage는 retry/reprocess 판단을 하지 않는다.
* 모든 정책 판단은 failcheck + Resolver에서 수행한다.

---

## 33.9 금지 사항

다음 구현은 금지한다.

* 일부 entity 실패 시 전체 rollback
* store 성공 상태를 fail로 변경
* 성공한 entity까지 재처리
* fail ledger 없이 실패 무시
* Stage 내부에서 retry/reprocess 판단

---

## 33.10 최종 정리

partial_failure는 허용한다.

처리 기준:

* store 실패 → 전체 fail
* store 성공 + 일부 entity 실패 → partial_failure

재처리 기준:

* 실패한 entity만 retry/reprocess

이를 통해 다음을 보장한다.

1. 데이터 손실 방지
2. 효율적인 재처리
3. failcheck 기반 정책 일관성
4. Stage 책임 분리 유지

==================================================
33. partial_failure 세부 처리 규칙 (신규) END
=====================================
