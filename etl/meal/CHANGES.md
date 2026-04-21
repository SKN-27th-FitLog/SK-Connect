# Project Changes & Architecture Upgrades

기존의 단순 스크립트 방식에서 엔터프라이즈급 ETL 아키텍처로 전환하며 변경된 주요 포인트들입니다.

## 1. 기반 구조 (Core Architecture)
- **상수 분리 (Modular Constants)**: 하나의 `constants.py`에 몰려있던 책임을 `schema_constants`, `pipeline_constants`, `code_rules`로 분리하여 관리 포인트와 가독성을 높였습니다.
- **코드 리졸버 (Code Resolver) 독립**: `BaseProcessor` 내부에 섞여 있던 코드 조회 로직을 독립된 `CodeLoader`와 `CodeResolver` 레이어로 분리했습니다. 이를 통해 조회 정책(Exact Match 등)을 중앙에서 제어합니다.

## 2. 데이터 무결성 (Data Integrity)
- **스키마 계약 (Schema Contract) 도입**: DB 제약사항 기반의 검증 체계를 도입했습니다. 필수 컬럼 누락 시 Default 값 보전에 우선하여 Fail 조치하는 엄격한 정책을 적용합니다.
- **Null 정의 표준화**: `""`, `" "`, `None`, `NaN`을 모두 하나의 Null 계열로 통합 관리하여 데이터 일관성을 확보했습니다.

## 3. 적재 및 중복 관리 (Loading & Deduplication)
- **BaseLoader 고도화**: Loader의 비대화를 막기 위해 `Validator`, `SyncService`, `FailureRecorder`로 책임을 분산하고 `BaseLoader`는 이들의 조율만 담당하게 변경했습니다.
- **계층적 중복 판별**: `source_url`을 기본으로 하되, 보조적으로 `(name + address)` 조합을 사용하는 이중 검증 체계를 구축했습니다.

## 4. 운영 및 자동화 (Operation)
- **Recovery Mode 고도화**: 단순히 파일을 재읽기하는 수준을 넘어, 실패 메타데이터(`retry_count`, `last_attempt_at` 등)를 추적하며 성공 시 `archive`로 이동하는 상태 관리형 복구 로직을 도입했습니다.
- **일일 수집 한도 (Quota)**: "실제 신규 성공 적재된 Shop 수"를 기준으로 일일 작업량을 정밀하게 제어합니다.

## 5. 검증 환경 (Testing)
- **독립 테스트 환경**: `tests/` 디렉토리를 신설하여 각 모듈(Resolver, Validator, Loader)의 독립적인 작동을 보장하는 단위 테스트 체계를 마련했습니다.
