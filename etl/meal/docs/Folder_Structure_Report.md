# 폴더 구조 규칙 분석 리포트

작성일: 2026-04-28  
분석 범위: 프로젝트 전체 기능 분석이 아니라, 폴더 구조와 책임 분리 규칙 중심

## 1. 요약

이 프로젝트는 맛집 데이터 ETL 파이프라인을 `crawl -> process -> save -> failcheck`라는 독립 실행 프로젝트 단위로 나누고, 공통 기능은 `src/core` 아래 계층별로 분리하는 구조를 사용한다.

핵심 구조 규칙은 다음과 같다.

1. 실행 단위는 `src/projects/{crawl,process,save,failcheck}`로 나눈다.
2. 각 프로젝트 내부는 `handler -> service -> stage` 흐름을 따른다.
3. Stage는 데이터 처리만 담당하고, 정책 판단은 `core/policy`와 `failcheck` 쪽으로 분리한다.
4. 플랫폼별 수집/파싱 코드는 `collectors/platforms`, `services/parsers`에 각각 둔다.
5. DB 접근, 저장 경로, 정책, 모델, 유틸리티는 `src/core` 하위 전용 폴더로 분리한다.
6. 중간 산출물은 코드 패키지 밖의 Hive 스타일 데이터 폴더에 저장한다.

현재 구조는 `docs/Design.MD`에 정의된 설계 방향과 대체로 일치하며, 폴더 이름만 보아도 실행 흐름과 책임 경계를 추적할 수 있게 구성되어 있다.

## 2. 현재 루트 구조

현재 루트의 주요 구성은 다음과 같다.

```text
meal/
├── src/                         # 실제 ETL 애플리케이션 코드
├── docs/                        # 설계/검토/분석 문서
├── backup/                      # 보조 또는 과거 점검 스크립트
├── diningcode_real_lake/        # 실행 산출물로 보이는 로컬 lake 데이터
├── run_snapshot/                # 로컬 실행 결과 확인용 스냅샷
├── local_pipeline_runner.py     # 로컬 통합 실행기
├── LOCAL_RUNNER_GUIDE.md        # 로컬 실행 가이드
├── requirements.txt             # Python 의존성
├── target.csv                   # 수집 대상 seed
└── target.example.csv           # 수집 대상 seed 예시
```

루트에는 애플리케이션 코드, 문서, 로컬 실행 도구, 실행 산출물이 함께 존재한다. 운영 코드의 중심은 `src`이고, `diningcode_real_lake`, `run_snapshot`, `.pytest_cache`, `.venv`, `__pycache__`는 코드 구조라기보다 실행 환경 또는 산출물 성격이 강하다.

## 3. `src` 하위 구조 규칙

```text
src/
├── collectors/
│   ├── base_collector.py
│   └── platforms/
│       ├── diningcode_collector.py
│       ├── google_collector.py
│       ├── kakao_collector.py
│       └── naver_collector.py
├── core/
│   ├── base_stage.py
│   ├── config.py
│   ├── constants.py
│   ├── dispatch.py
│   ├── registry.py
│   ├── models/
│   ├── policy/
│   ├── repository/
│   ├── storage/
│   └── utils/
├── projects/
│   ├── crawl/
│   ├── process/
│   ├── save/
│   └── failcheck/
└── services/
    └── parsers/
```

### 3.1 `src/projects`: 실행 프로젝트 단위

`src/projects`는 업무 흐름 기준으로 나뉜다.

| 폴더 | 담당 |
|---|---|
| `crawl` | 대상 선정과 원본 수집 |
| `process` | 원본 파싱, 검증, 정규화 |
| `save` | 정규화 결과의 DB 적재 |
| `failcheck` | 실패 데이터 수집, 정책 판단, 후속 action 분류 |

각 프로젝트 폴더 내부는 공통적으로 다음 패턴을 따른다.

```text
{project}_handler.py   # Lambda/CLI 진입점
{project}_service.py   # 프로젝트 실행 orchestration
stageN_*.py            # 실제 데이터 처리 단계
__init__.py
```

예시는 다음과 같다.

```text
src/projects/crawl/
├── crawl_handler.py
├── crawl_service.py
├── stage0_target_selection.py
└── stage1_raw_collection.py

src/projects/process/
├── process_handler.py
├── process_service.py
├── stage2_candidate_parsing.py
└── stage3_validation_normalization.py
```

이 구조에서는 `handler`가 외부 실행 진입점, `service`가 stage 연결과 입출력 흐름, `stage`가 실제 처리를 담당한다.

### 3.2 `src/core`: 공통 기반 계층

`core`는 특정 프로젝트에 종속되지 않는 공통 로직을 담는다.

| 폴더/파일 | 역할 |
|---|---|
| `base_stage.py` | 모든 stage의 공통 추상 기반 |
| `config.py` | 환경 설정 |
| `constants.py` | SQL 등 상수 |
| `registry.py` | stage, collector, parser, repository 등록 및 생성 |
| `dispatch.py` | failcheck action 결과를 후속 경로로 분배 |
| `models/` | 공통 데이터 모델 |
| `policy/` | reason_code, exception, resolver, fail_record |
| `repository/` | DB 및 외부 저장소 접근 |
| `storage/` | JSONL 저장, Hive path 생성 |
| `utils/` | batch, hash 등 범용 유틸리티 |

구조상 중요한 규칙은 `core`가 프로젝트별 흐름을 직접 소유하지 않고, 프로젝트들이 공통 기능을 가져다 쓰는 방향이라는 점이다.

### 3.3 `collectors`와 `services/parsers`: 플랫폼별 어댑터 분리

플랫폼별 수집과 파싱은 서로 다른 책임으로 분리되어 있다.

```text
src/collectors/platforms/{platform}_collector.py
src/services/parsers/{platform}_parser.py
```

현재 지원 플랫폼은 `DiningCode`, `Naver`, `Google`, `Kakao`이며, `registry.py`에서 collector/parser map으로 등록된다.

이 규칙의 장점은 새 플랫폼을 추가할 때 다음 파일만 확장하면 된다는 점이다.

1. `src/collectors/platforms/new_platform_collector.py`
2. `src/services/parsers/new_platform_parser.py`
3. `src/core/registry.py` 등록

## 4. Stage 배치 규칙

설계 문서와 실제 코드 기준으로 stage는 다음처럼 프로젝트에 배치된다.

| Stage | 이름 | 위치 |
|---|---|---|
| Stage 0 | Daily Target Selection | `projects/crawl/stage0_target_selection.py` |
| Stage 1 | Raw Collection | `projects/crawl/stage1_raw_collection.py` |
| Stage 2 | Candidate Parsing | `projects/process/stage2_candidate_parsing.py` |
| Stage 3 | Validation & Normalization | `projects/process/stage3_validation_normalization.py` |
| Stage 4 | Load | `projects/save/stage4_load.py` |
| Stage 5 | Fail Classification | `projects/failcheck/stage5_fail_classification.py` |

여기서 중요한 규칙은 "stage 번호가 폴더를 결정하는 것이 아니라, 프로젝트 책임이 폴더를 결정한다"는 점이다. 예를 들어 Stage 2와 Stage 3은 둘 다 `process` 책임이므로 같은 폴더에 있다.

## 5. 실행 흐름에 따른 폴더 연결 규칙

프로젝트 간 직접 함수 호출보다는 저장된 산출물 경로를 통해 느슨하게 연결되는 구조다.

```text
crawl success
  -> process 입력

process success
  -> save 입력

crawl/process/save fail
  -> failcheck 입력
```

실제 서비스 코드도 이 규칙을 따른다.

| 서비스 | 입력 탐색 기준 | 출력 |
|---|---|---|
| `CrawlService` | target seed / source pool | raw success/fail |
| `ProcessService` | raw success JSONL | normalized success/fail |
| `SaveService` | normalized success JSONL | load success/fail |
| `FailcheckService` | raw/process/load fail JSONL | retry/reprocess/drop/warning 계열 |

따라서 폴더 구조상 `projects` 사이의 결합은 낮고, `core/storage/path_builder.py`가 프로젝트 간 데이터 위치 규약을 강하게 통제한다.

## 6. 저장 경로 규칙

중간 산출물은 Hive 스타일 파티션 경로를 사용한다.

기본 형식은 다음과 같이 단순화하는 방향을 권장한다.

```text
process={raw|cleansing|save|failcheck}/
category_cd={category_cd}/
year=YYYY/month=MM/day=DD/
status={success|fail|pending|final_drop|check}/
```

기존의 `stage={stage_name}`과 `batch_id={batch_id}`는 폴더 파티션에서 제거하되, 추적성을 잃지 않도록 파일명과 JSONL 레코드 내부 필드에 반드시 유지한다.

```text
{stage_name}_{batch_id}_{YYMMDDHHMMSS}.jsonl
```

예시는 다음과 같다.

```text
process=raw/category_cd=CA01/year=2026/month=04/day=28/status=success/raw_collection_20260428_CA01_001_260428153012.jsonl
process=cleansing/category_cd=CA01/year=2026/month=04/day=28/status=success/validation_normalization_20260428_CA01_001_260428153045.jsonl
```

`save` 영역은 테이블 단위 구분을 위해 날짜 파티션 뒤에 `save={table_name}`이 추가된다.

```text
process=save/category_cd=CA01/year=2026/month=04/day=28/save=shop/status=success/load_20260428_CA01_001_260428153100.jsonl
```

이 구조에서는 폴더 깊이를 줄이면서도 다음 정보를 유지해야 한다.

| 정보 | 저장 위치 |
|---|---|
| 처리 영역 | `process` 파티션 |
| 카테고리 | `category_cd` 파티션 |
| 실행 날짜 | `year/month/day` 파티션 |
| 성공/실패 상태 | `status` 파티션 |
| stage 이름 | 파일명 prefix + JSONL 내부 `stage` 필드 |
| batch_id | 파일명 + JSONL 내부 `batch_id` 필드 |
| run_attempt | JSONL 내부 `run_attempt` 필드, 필요 시 파일명 suffix |

`stage`를 경로에서 제거할 때의 핵심 주의점은 `process=cleansing` 아래에 `candidate_parsing`과 `validation_normalization`이 함께 들어간다는 점이다. 따라서 파일명 prefix에 stage 이름을 넣지 않으면 같은 날짜/status 안에서 Stage 2와 Stage 3 결과를 경로만으로 구분하기 어렵다.

`batch_id`도 경로에서는 제거할 수 있지만, 개념 자체를 삭제해서는 안 된다. `batch_id`는 `crawl -> process -> save -> failcheck` 사이에서 같은 실행 묶음을 연결하는 기준이므로 파일명과 레코드 내부에는 계속 남긴다.

`HivePathBuilder`는 내부 process 이름을 외부 저장 파티션으로 정규화한다.

| 내부 process | 저장 파티션 |
|---|---|
| `candidate` | `cleansing` |
| `normalized` | `cleansing` |
| `load` | `save` |
| `retry` | `failcheck` |
| `reprocess` | `failcheck` |
| `dropped` | `failcheck` |
| `warning` | `failcheck` |

파일명은 경로에서 제거된 `stage`와 `batch_id`를 보완해야 하므로 다음 규칙을 따른다.

| 대상 | 파일명 규칙 |
|---|---|
| 일반 JSONL | `{stage_name}_{batch_id}_{YYMMDDHHMMSS}.jsonl` |
| save 테이블 CSV | `{table_name}_HHMMSS.csv` |
| save attempt 포함 JSONL | `{stage_name}_{batch_id}_{YYMMDDHHMMSS}_att{run_attempt}.jsonl` |
| failcheck action 파일 | `retry_items.jsonl`, `reprocess_items.jsonl`, `drop_items.jsonl`, `warning_summary.jsonl` |

## 7. 정책/판단 로직 위치 규칙

폴더 구조에서 반복되는 가장 중요한 아키텍처 규칙은 "처리와 판단의 분리"다.

| 책임 | 위치 |
|---|---|
| 데이터 처리 | `projects/*/stage*.py` |
| 실패 의미 표현 | `core/policy/exceptions.py`, `reason_code.py` |
| action 결정 | `core/policy/resolver.py` |
| 실패 기록 구조 | `core/policy/fail_record.py` |
| 실패 후속 분류 | `projects/failcheck` |
| 후속 action 저장 | `core/dispatch.py` |

즉, `crawl`, `process`, `save`는 retry/reprocess/drop/alert 같은 최종 정책 판단을 하지 않는 것이 구조 규칙이다. 실패는 fail JSONL로 남기고, `failcheck`가 후속 판단을 담당한다.

## 8. 신규 코드 추가 시 폴더 선택 규칙

새 코드를 추가할 때는 다음 기준으로 위치를 정하면 된다.

| 추가하려는 코드 | 권장 위치 |
|---|---|
| 새 실행 업무 단위 | `src/projects/{new_project}` |
| 기존 crawl/process/save/failcheck의 처리 단계 | 해당 `src/projects/{project}/stageN_*.py` |
| Lambda 또는 CLI 진입점 | 해당 `*_handler.py` |
| 여러 stage를 연결하는 orchestration | 해당 `*_service.py` |
| 플랫폼별 수집 코드 | `src/collectors/platforms` |
| 플랫폼별 HTML/JSON 파싱 코드 | `src/services/parsers` |
| DB 조회/저장 | `src/core/repository` |
| 경로/파일 저장 규칙 | `src/core/storage` |
| 실패 reason/action 정책 | `src/core/policy` |
| batch/hash 등 범용 로직 | `src/core/utils` |
| 공통 데이터 구조 | `src/core/models` |

반대로 피해야 할 배치는 다음과 같다.

1. Stage 내부에 retry/reprocess/drop 판단을 넣는 것
2. 프로젝트 폴더 안에 DB 연결 공통 로직을 직접 구현하는 것
3. collector 안에 parsing/normalization 정책을 과도하게 넣는 것
4. parser 안에 DB 저장이나 failcheck 정책을 넣는 것
5. 저장 경로 문자열을 각 service/stage에서 직접 조립하는 것
6. 새 플랫폼을 추가하면서 `registry.py` 등록을 누락하는 것

## 9. 현재 구조의 장점

1. 실행 책임이 프로젝트 단위로 분명하다.
2. `handler`, `service`, `stage`의 역할이 비교적 일관적이다.
3. 플랫폼별 수집/파싱 확장 지점이 분리되어 있다.
4. 저장 경로 규칙이 `HivePathBuilder`에 집중되어 있다.
5. 실패 정책이 `failcheck`와 `resolver` 중심으로 모여 있어 stage가 과도하게 똑똑해지는 것을 막는다.
6. AWS Lambda, 로컬 실행기, batch/shard 실행을 고려한 구조가 이미 반영되어 있다.

## 10. 구조상 주의점 및 개선 제안

### 10.1 실행 산출물과 코드 폴더 분리 강화

현재 루트에는 `diningcode_real_lake`, `run_snapshot`, `.pytest_cache`, `__pycache__` 같은 실행 산출물이 보인다. 이들은 코드 구조 분석 시 혼선을 줄 수 있으므로 `.gitignore`와 운영 문서에서 "산출물 폴더"로 명확히 분류하는 것이 좋다.

권장 분류:

```text
runtime/
├── lake/
└── snapshots/
```

또는 현재처럼 유지하더라도 README/문서에서 코드 폴더가 아님을 명시하는 편이 좋다.

### 10.2 `services/parsers` 명명 검토

`services`라는 이름은 일반적으로 비즈니스 orchestration 계층처럼 보일 수 있다. 이 프로젝트에서는 실제 orchestration이 `projects/*/*_service.py`에 있으므로, 장기적으로는 다음 중 하나가 더 명확할 수 있다.

```text
src/parsers/
```

또는

```text
src/adapters/parsers/
src/adapters/collectors/
```

다만 현재 규모에서는 반드시 바꿀 필요는 없다. 새 참여자가 혼동할 수 있는 지점이라는 정도로 보면 된다.

### 10.3 `backup` 폴더의 성격 명시

`backup/check_progress.py`는 현재 구조상 운영 코드인지 임시 보조 도구인지 애매하다. 계속 사용할 스크립트라면 `tools/` 또는 `scripts/`로 이동하고, 정말 백업이면 운영 코드와 구분되도록 문서화하는 것이 좋다.

### 10.4 테스트 폴더 상태 확인 필요

`git status` 기준으로 `tests/test_content_hash.py`, `tests/test_design_contracts.py`, `tests/test_stage3_hash_fields.py`가 삭제 상태로 보인다. 현재 작업트리에는 `tests/` 폴더가 보이지 않으므로, 폴더 구조 규칙 문서에는 테스트 구조가 확정되어 있지 않은 상태로 기록하는 것이 맞다.

권장 테스트 구조:

```text
tests/
├── core/
├── projects/
├── collectors/
└── services/
```

## 11. 최종 폴더 구조 규칙 초안

이 프로젝트에서 앞으로 지키면 좋은 폴더 구조 규칙은 다음과 같이 정리할 수 있다.

1. `src/projects`는 독립 실행 가능한 ETL 프로젝트 단위로만 나눈다.
2. 각 프로젝트는 `handler`, `service`, `stage` 세 계층을 유지한다.
3. Stage 파일은 데이터 처리만 담당하고 정책 action 결정은 하지 않는다.
4. 공통 정책, 저장, DB, 모델, 유틸은 반드시 `src/core`로 올린다.
5. 플랫폼별 외부 연동 코드는 collector/parser 어댑터로 분리한다.
6. 프로젝트 간 데이터 전달은 직접 호출보다 Hive 스타일 산출물 경로를 기준으로 한다.
7. 저장 경로와 파일명은 `HivePathBuilder`와 `JsonlWriter`를 통해서만 생성한다.
8. 실패 후속 판단은 `projects/failcheck`와 `core/policy/resolver.py`에 집중한다.
9. 실행 산출물은 코드 패키지와 분리하고, 루트에 둘 경우 명확히 문서화한다.
10. 새 폴더를 만들기 전 기존 계층 중 어느 책임에 속하는지 먼저 판단한다.

## 12. 결론

현재 프로젝트의 폴더 구조는 단순한 기능별 분리가 아니라, ETL 실행 흐름과 정책 책임 분리를 함께 표현하는 구조다. `projects`는 실행 흐름, `core`는 공통 기반, `collectors/parsers`는 플랫폼 어댑터, lake 경로는 데이터 전달 계약이라는 역할을 가진다.

가장 중요한 유지 원칙은 다음 한 문장으로 요약할 수 있다.

> 프로젝트 폴더는 실행 단위를 표현하고, core 폴더는 공통 계약을 표현하며, stage는 처리만 하고 정책 판단은 failcheck/resolver로 보낸다.
