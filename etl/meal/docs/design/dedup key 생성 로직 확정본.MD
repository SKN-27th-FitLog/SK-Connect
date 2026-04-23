==================================================
[dedup key 생성 로직 확정본]
==================================================

1. 목적
dedup key는 동일 store를 중복 없이 식별하기 위한 운영 기준 키이다.

본 시스템에서 dedup key는 다음 목적에 사용한다.

- 동일 store의 중복 수집 방지
- 동일 batch 내 중복 target 판정
- 기존 적재 store와 신규 수집 store의 동일성 판정
- DB upsert 기준 키 생성
- fail/retry/reprocess 시 동일 store 추적

2. 기본 원칙
dedup key는 단일 필드만으로 무조건 판정하지 않는다.
판정 가능한 정보의 신뢰도에 따라 우선순위를 두고 생성한다.

우선순위는 다음과 같다.

1) canonical_url
2) normalized_name + normalized_address
3) source_platform + source_internal_id

상위 우선순위 키를 사용할 수 있으면 하위 우선순위 키는 판정 기준으로 사용하지 않는다.
하위 키는 보조 비교 정보로만 저장할 수 있다.

3. 우선순위별 정의

3.1 canonical_url
canonical_url은 동일 store를 대표하도록 정규화된 URL이다.

정규화 예시
- query parameter 제거
- utm 등 추적 파라미터 제거
- trailing slash 제거
- scheme 통일(http/https 정책 기준)
- 불필요한 fragment 제거

canonical_url이 존재하고 유효하면 최우선 dedup key로 사용한다.

예:
https://example.com/store/123
https://example.com/store/123?utm_source=abc
-> 동일 canonical_url로 정규화 가능

3.2 normalized_name + normalized_address
canonical_url이 없거나 신뢰할 수 없는 경우,
정규화된 상호명과 정규화된 주소를 결합하여 dedup key로 사용한다.

정규화 예시
- 상호명 공백 정리
- 불필요한 특수문자 제거
- 대소문자 정책 통일
- 주소 표기 통일
- 시/도/구/동 표현 정규화
- 약어/축약어 정리

결합 형식 예시
{name_normalized}|{address_normalized}

예:
맛있는초밥본점|서울특별시강남구테헤란로123

3.3 source_platform + source_internal_id
canonical_url도 없고 normalized_name + normalized_address도 불완전할 경우,
플랫폼 내부 식별자를 fallback dedup key로 사용한다.

주의
- source_internal_id 단독 사용은 금지한다.
- 반드시 source_platform과 함께 묶어 사용한다.

결합 형식 예시
{source_platform}|{source_internal_id}

예:
naver_map|12345
kakao_map|12345

위 두 값은 서로 다른 store로 간주한다.

4. dedup key 생성 조건

4.1 canonical_url 사용 조건
아래 조건을 모두 만족할 때 사용한다.
- canonical_url이 null/empty가 아님
- URL 정규화 완료
- 대표 URL로 신뢰 가능
- blacklist 또는 invalid url 패턴에 해당하지 않음

4.2 normalized_name + normalized_address 사용 조건
아래 조건을 모두 만족할 때 사용한다.
- normalized_name이 null/empty가 아님
- normalized_address가 null/empty가 아님
- 둘 다 정규화 완료
- placeholder 값(예: unknown, 미정, null 문자열)이 아님

4.3 source_platform + source_internal_id 사용 조건
아래 조건을 모두 만족할 때 사용한다.
- source_platform이 null/empty가 아님
- source_internal_id가 null/empty가 아님
- 동일 플랫폼 내 식별자임이 보장됨

5. 생성 규칙
dedup key는 아래 절차에 따라 생성한다.

Step 1.
canonical_url 사용 가능 여부 확인

Step 2.
가능하면 dedup_key_type = canonical_url
dedup_key_value = normalized canonical_url

Step 3.
canonical_url 사용 불가 시 normalized_name + normalized_address 사용 가능 여부 확인

Step 4.
가능하면 dedup_key_type = name_address
dedup_key_value = "{normalized_name}|{normalized_address}"

Step 5.
위 둘 다 불가 시 source_platform + source_internal_id 사용 가능 여부 확인

Step 6.
가능하면 dedup_key_type = platform_internal_id
dedup_key_value = "{source_platform}|{source_internal_id}"

Step 7.
셋 다 불가하면 dedup_key 생성 실패로 기록하고 reason_code를 남긴다.

6. 저장 규칙
dedup 판정의 투명성을 위해 단일 dedup_key_value만 저장하지 않고,
아래 정보를 함께 저장한다.

- dedup_key_type
- dedup_key_value
- canonical_url 원본/정규화 값
- normalized_name
- normalized_address
- source_platform
- source_internal_id

예시
{
  "dedup_key_type": "name_address",
  "dedup_key_value": "맛있는초밥본점|서울특별시강남구테헤란로123",
  "canonical_url": null,
  "normalized_name": "맛있는초밥본점",
  "normalized_address": "서울특별시강남구테헤란로123",
  "source_platform": "naver_map",
  "source_internal_id": "12345"
}

7. 판정 규칙

7.1 동일성 판정
동일 dedup_key_type과 동일 dedup_key_value를 가지면 동일 store 후보로 본다.

7.2 상위 우선순위 우선 원칙
동일 store에 대해 복수 키가 동시에 존재하더라도
항상 가장 높은 우선순위 키를 기준 dedup key로 채택한다.

예:
- canonical_url 있음
- normalized_name + normalized_address 있음
-> canonical_url 기준으로 판정

7.3 하위 키의 역할
하위 우선순위 키는 기준 판정 키가 아니라 보조 검증 정보로 저장한다.

7.4 판정 불가
세 가지 키 모두 생성 불가능하면 dedup 판정 불가로 보고
즉시 중복 판정을 수행하지 않는다.
이 경우 reason_code를 기록하고 후속 정책에 따라 fail 또는 reprocess 대상으로 분류한다.

8. reason_code 규칙
dedup key 생성 실패 또는 품질 이슈 시 다음 예시 reason_code를 사용할 수 있다.

- DEDUP_KEY_NOT_GENERATABLE
- INVALID_CANONICAL_URL
- MISSING_NORMALIZED_NAME
- MISSING_NORMALIZED_ADDRESS
- MISSING_PLATFORM_INTERNAL_ID
- CONFLICTING_DEDUP_SIGNALS

9. 충돌 규칙
복수의 키 정보가 서로 모순될 경우 자동으로 동일 store 확정하지 않는다.

예:
- canonical_url은 기존 store A와 일치
- normalized_name + normalized_address는 store B와 유사

이 경우:
- 최우선 기준은 canonical_url이지만
- 충돌 이벤트를 별도 기록할 수 있다.
- reason_code = CONFLICTING_DEDUP_SIGNALS
- 운영 검토 또는 후속 재처리 대상으로 분류 가능

10. DB 연계 원칙
DB upsert 및 unique 판정 기준은 dedup_key_value 단독이 아니라
dedup_key_type + dedup_key_value 조합으로 관리하는 것을 권장한다.

예:
- canonical_url|https://example.com/store/123
- name_address|맛있는초밥본점|서울특별시강남구테헤란로123
- platform_internal_id|naver_map|12345

이렇게 해야 서로 다른 key type 간 우연한 문자열 충돌을 방지할 수 있다.

11. 운영 주의사항
- dedup key는 store 식별용이며 batch_id를 대체하지 않는다.
- dedup key는 category_cd와 독립적으로 관리한다.
- 동일 batch 내 중복 제거와 전체 DB 기준 중복 제거에 모두 재사용할 수 있어야 한다.
- 정규화 정책이 바뀌면 dedup 결과도 달라질 수 있으므로 버전 관리가 필요할 수 있다.

12. 권장 추가 필드
운영 추적을 위해 아래 필드를 함께 저장하는 것을 권장한다.

- dedup_rule_version
- dedup_generated_at
- dedup_confidence (선택)
- dedup_conflict_flag

[dedup key 우선순위 확정]

동일 store 판정은 아래 우선순위에 따라 수행한다.

1) canonical_url
2) normalized_name + normalized_address
3) source_platform + source_internal_id

상위 우선순위 키를 사용할 수 있는 경우 하위 키는 기준 판정에 사용하지 않는다.
하위 키는 보조 검증 정보로만 저장할 수 있다.

dedup key는 dedup_key_type과 dedup_key_value를 함께 저장하며,
세 가지 기준 모두 생성 불가한 경우 reason_code를 기록하고 dedup 판정 불가 상태로 처리한다.