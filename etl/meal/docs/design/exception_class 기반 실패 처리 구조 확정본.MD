[exception_class 기반 실패 처리 구조 확정본]


1. # 저장 방식

기존:

- fail policy를 DB 테이블로 관리

변경:

- 실패 처리 정책은 DB 테이블이 아니라 Exception class 기반으로 관리한다.

- Exception class는 실패의 "의미(reason_code)"를 정의한다.

- 운영 정책(action, severity 등)은 별도 resolver에서 결정한다.

 2. 설계 원칙


1. Exception class 역할

- 실패의 타입 정의
- reason_code 정의
- 실패 context 저장 (stage, entity_type, detail)

2. Resolver 역할

- action 결정
- severity 결정
- retry 정책 결정
- include_in_next_batch 여부 결정

3. Fail Ledger 역할

- 운영 데이터 기록
- reason_code/action 기반 기록

4. CloudWatch 역할

- 로그 기반 감시
- 알람 생성
- 메트릭 집계

 3. Exception Class 정의 원칙

class CrawlerException(Exception):
reason_code = "UNKNOWN_ERROR"

```
def __init__(self, message="", *, stage=None, entity_type="common", detail=None):
    super().__init__(message)
    self.stage = stage
    self.entity_type = entity_type
    self.detail = detail or {}
```

예시:

class NetworkError(CrawlerException):
reason_code = "NETWORK_ERROR"

class SelectorMismatchError(CrawlerException):
reason_code = "SELECTOR_MISMATCH"

 4. Resolver 설계 원칙

- Exception class는 action을 직접 결정하지 않는다.
- resolver가 reason_code + stage + entity_type 기준으로 action을 결정한다.

예시:

resolve_failure_meta(exception):
return {
reason_code,
stage,
entity_type,
action,
severity,
retry_count,
}

 5. Fail Ledger 기록 원칙

필수 필드:

- stage
- reason_code
- action
- entity_type
- entity_id
- failed_at

추가 필드:

- reason_detail
- retry_count
- source_url
- raw_path

 6. CloudWatch 로그 원칙

모든 실패 로그는 구조화된 형태로 출력한다.

예시:

{
"event": "crawler_failure",
"reason_code": "NETWORK_ERROR",
"stage": "raw_collection",
"entity_type": "common",
"action": "retry",
"severity": "medium",
"batch_id": "..."
}

- CloudWatch는 해당 로그를 기반으로 알람을 생성한다.
- 애플리케이션은 알람 판단을 직접 수행하지 않는다.
