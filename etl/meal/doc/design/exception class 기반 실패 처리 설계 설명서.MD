[exception class 기반 실패 처리 설계 설명서]

1. 설계 목적

본 시스템은 크롤링 과정에서 발생하는 실패를
Exception class 기반으로 정의하고,
resolver를 통해 후속 처리 정책을 결정한다.

기존:

* DB 테이블 기반 정책 관리

변경:

* Exception class + resolver 기반 처리

2. 핵심 설계 개념


(1) 실패 의미와 운영 정책 분리

* Exception class: 실패 의미 정의
* Resolver: 운영 정책 결정

(2) 실행 흐름

Exception 발생
→ Exception class 전달
→ Resolver가 action 결정
→ Fail Ledger 기록
→ CloudWatch 로그 출력

3. 설계 장점

* 코드 가독성 향상
* 실패 원인 추적 용이
* DB 의존성 제거
* CloudWatch 기반 관측성 강화

4. 주의사항

* Exception class에 운영 정책을 과도하게 넣지 않는다
* retry_count 등 운영 값은 resolver에서 관리한다
* stage/entity_type은 context로 전달한다
