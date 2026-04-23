# [Spec] 상수 정리 및 표준화 (Constants Cleanup & Standardization)

## 1. 개요
현재 `src/core/constants/pipeline_constants.py`에 정의된 데이터 중 상당수가 실제 코드에서 사용되지 않고 있으며, 반대로 코드 내에는 하드코딩된 문자열(예: `"DCODE"`, `"review"`)들이 산재해 있습니다. 이를 정리하고 단일 관리 포인트로 통합하여 코드 품질과 유지보수성을 높입니다.

## 2. 변경 내역

### 2.1 `pipeline_constants.py` 정리
- **유지**:
  - `CrawlerThread` 클래스 (SHOP, REVIEW 멤버 유지)
  - `LoadStatus` 클래스 (SUCCESS, FAIL 멤버 유지)
- **추가**:
  - `PlatformSource` 클래스: `DININGCODE = "DCODE"` 추가
- **삭제**:
  - `ProcessType` (미사용)
  - `Status` (ST01, ST02 - 현재 로직에서 미사용)
  - `PipelineQuota` (하드코딩된 설정값으로 현재 오케스트레이터에서 미사용)

### 2.2 적용 대상 (Refactoring)
- **`StoreRepository.py`**:
  - `shop_cd = "DCODE"`를 `PlatformSource.DININGCODE.value`로 교체
  - `INSERT_CRAWLING` 시 `"review"` 문자열을 `CrawlerThread.REVIEW.value`로 교체
- **`HttpCollector.py`**:
  - 응답 딕셔너리의 `"status": "success"/"fail"`을 `LoadStatus` 상수로 교체
- **`OrchestratorV4.py` / `LoadPipeline.py`**:
  - 수집 결과 확인 및 로그 메시지 내 상태값을 상수로 교체

## 3. 기대 효과
- 미사용 코드를 제거하여 코드베이스 경량화
- 하드코딩된 문자열을 상수로 통합하여 플랫폼 코드나 스레드 명칭 변경 시 유연한 대응 가능
- 전반적인 데이터 흐름의 일관성 확보

## 4. 자가 검토 (Self-Review)
- **Placeholder**: 없음. 모든 상수의 의미와 적용 위치가 정의됨.
- **일관성**: `schema_constants.py`에 정의된 컬럼명들과 충돌하지 않음을 확인.
- **범위**: 단순히 상수 정리와 적용에 국한됨 (리뷰 빈 칸 필터링은 제외됨).
