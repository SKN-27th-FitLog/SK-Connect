# IC02 IT 키워드 입력 전처리 설계

## 목적

`ai/post_analysis`의 IC02 IT 뉴스 키워드 추출에서 Ollama `gemma4:26b` 입력을 안정적으로 줄인다.

현재 `analyze_it_keywords`는 `analysis.content`를 거의 그대로 prompt에 넣는다. `gemma4:26b`가 CPU로 실행되는 환경에서는 짧은 테스트 prompt도 수십 초가 걸리고, 실제 IC02 row prompt는 120초 timeout을 넘길 수 있다. 따라서 IC02 전용 LLM 입력 전에 원문 발췌 기반 전처리와 검증을 추가한다.

이 설계는 기존 IC01 맛집 분석과 BERT 키워드 추출을 변경하지 않는다.

## 범위

포함한다.

- `ai/post_analysis` 내부 IC02 키워드 추출 입력 전처리만 변경한다.
- `analysis.content` 원문에서 중요한 문단·문장을 발췌해 LLM 입력용 `compressed_content`를 만든다.
- 전처리 결과가 원문에서 벗어나지 않았는지 검증한다.
- 긴 원문은 실제로 압축됐는지 검증한다.
- 검증 실패 row는 LLM 호출 없이 스킵하고 오류 로그를 남긴다.
- 전처리 기본값은 IC02 전용 config/env로 조절 가능하게 한다.

포함하지 않는다.

- `etl/it_news` 크롤링·클리닝·save 변경
- `etl/meal` 변경
- IC01 `get_reviews`, `analyze_sentimental`, `analyze_keywords` 동작 변경
- `ai/postmake_pipeline` 변경
- DB 스키마 변경
- LLM이 요약문을 먼저 생성하는 방식

## 핵심 원칙

전처리는 **생성 요약이 아니라 원문 발췌 압축**이어야 한다.

즉, LLM에 전달하는 `compressed_content`는 원문에 실제로 존재하는 문단 또는 문장 조각만 포함한다. 전처리 단계에서 새 문장을 만들거나 의미를 재작성하지 않는다. 그래야 원문 이탈 검증이 가능하다.

## 처리 흐름

```text
original_content
→ normalize_it_content
→ split_content_units
→ score_content_units
→ select_content_units
→ rebuild_compressed_content
→ validate_preprocessed_content
→ build_it_keyword_prompt
→ Ollama 호출
```

`title`은 그대로 유지한다. `content`만 LLM 입력 전용으로 압축한다.

## 전처리 상세

### 1. 정규화

원문 content에 다음 정규화를 적용한다.

- HTML entity를 사람이 읽는 문자로 변환한다.
- `\r\n`, `\r`, 여러 개의 공백을 정리한다.
- 빈 줄은 문단 경계로 유지하되, 3개 이상 연속 빈 줄은 하나의 경계로 줄인다.
- 앞뒤 공백을 제거한다.

정규화는 의미를 바꾸지 않는 문자 수준 정리만 수행한다.

### 2. 문단·문장 단위 분리

우선 문단 단위로 나눈다.

문단 하나가 너무 길면 문장 단위로 다시 나눈다. 문장 경계는 마침표, 물음표, 느낌표, 줄바꿈, 한국어 종결 표현을 기준으로 보수적으로 잡는다. 경계 판단이 애매하면 문단을 무리하게 쪼개지 않는다.

### 3. 중요도 점수

각 unit은 deterministic 점수로 정렬한다. 점수는 LLM을 쓰지 않는다.

가점 기준:

- 첫 문단
- 마지막 문단
- title에 포함된 영문/숫자/한글 핵심 토큰과 겹침
- 버전·모델·제품명처럼 보이는 토큰 포함
- 숫자 포함
- IT 관점 단어 포함

초기 IT 관점 단어:

```text
AI, LLM, 모델, 추론, 학습, 배포, GPU, CPU, 성능, 비용, 보안, 취약점,
릴리스, 버전, 업데이트, 프레임워크, API, 오픈소스, 라이선스, 데이터,
개발자, 에이전트, 자동화, 클라우드, 인프라, 영향, 리스크, 활용
```

동점이면 원문 순서를 유지한다.

### 4. 선택과 재조립

기본 제한값:

- `MAX_CONTENT_CHARS = 2500`
- `MAX_CONTENT_UNITS = 8`

선택 규칙:

1. 첫 unit은 가능하면 포함한다.
2. 점수 높은 unit을 예산 안에서 선택한다.
3. 선택된 unit은 원문 순서대로 다시 정렬해 재조립한다.
4. unit 사이에는 빈 줄 하나를 넣는다.
5. 예산을 넘는 unit은 포함하지 않는다.

단일 unit이 `MAX_CONTENT_CHARS`를 초과하면 문장 단위로 다시 쪼갠 뒤 같은 규칙으로 선택한다. 그래도 줄일 수 없으면 검증 실패로 처리한다.

## 검증 규칙

`validate_preprocessed_content(original, compressed, max_chars)`는 다음을 확인한다.

### 출처 검증

- `compressed`는 비어 있으면 안 된다.
- `compressed`를 구성하는 각 unit은 정규화된 원문 안에서 찾아야 한다.
- 원문에 없는 새 문장이나 재작성 문장이 포함되면 실패한다.

### 압축 검증

원문 길이가 `max_chars`보다 긴 경우:

- `compressed` 길이는 원문보다 짧아야 한다.
- `compressed` 길이는 `max_chars` 이하여야 한다.

원문 길이가 `max_chars` 이하인 경우:

- `compressed`가 원문과 같아도 정상이다.
- 그래도 출처 검증은 수행한다.

## 검증 실패 처리

검증 실패 row는 LLM 호출을 하지 않는다.

처리 방식:

- `logger.exception` 또는 `logger.error`로 `crawling_id`, index, 실패 사유를 남긴다.
- 해당 row는 성공 대상에서 제외한다.
- 다른 row 처리는 계속한다.
- 성공 row가 없으면 기존처럼 `merge_analysis_data`를 호출하지 않는다.

fallback으로 앞부분 truncate를 수행하지 않는다. 원문 그대로 LLM 호출도 하지 않는다.

## Config와 환경변수

IC02 전용 설정에 다음 값을 추가한다.

- `MAX_CONTENT_CHARS = 2500`
- `MAX_CONTENT_UNITS = 8`
- `MAX_UNIT_CHARS = 1200`
- `MAX_CONTENT_CHARS_ENV_KEY = "POST_ANALYSIS_IT_KEYWORDS_MAX_CONTENT_CHARS"`
- `MAX_CONTENT_UNITS_ENV_KEY = "POST_ANALYSIS_IT_KEYWORDS_MAX_CONTENT_UNITS"`
- `MAX_UNIT_CHARS_ENV_KEY = "POST_ANALYSIS_IT_KEYWORDS_MAX_UNIT_CHARS"`
- `REQUEST_TIMEOUT_SECONDS_ENV_KEY = "POST_ANALYSIS_IT_KEYWORDS_TIMEOUT_SECONDS"`

환경변수 값이 없거나 양의 정수가 아니면 기본값을 사용한다.

기존 `REQUEST_TIMEOUT_SECONDS = 120`도 `AnalyzeItKeywordsConfig`의 기본값으로 유지하되, 실행 환경에서 `POST_ANALYSIS_IT_KEYWORDS_TIMEOUT_SECONDS`로 override할 수 있게 한다.

## 설정 집중화와 하드코딩 금지

구현 코드에는 반복 숫자, prompt 라벨, scoring keyword, env key 문자열을 산발적으로 하드코딩하지 않는다.

다음 값은 `AnalyzeItKeywordsConfig`에 집중한다.

- 전처리 숫자 제한값
  - `MAX_CONTENT_CHARS`
  - `MAX_CONTENT_UNITS`
  - `MAX_UNIT_CHARS`
- 환경변수 key
  - `MAX_CONTENT_CHARS_ENV_KEY`
  - `MAX_CONTENT_UNITS_ENV_KEY`
  - `MAX_UNIT_CHARS_ENV_KEY`
  - `REQUEST_TIMEOUT_SECONDS_ENV_KEY`
- content unit scoring에 쓰는 IT 관점 단어 목록
  - `IMPORTANT_TERMS`
- prompt에 쓰는 고정 라벨
  - `TITLE_PROMPT_LABEL`
  - `COMPRESSED_CONTENT_PROMPT_LABEL`
  - `INTEREST_PROMPT_LABEL`
- LLM 응답 예시 schema 문자열
  - `RESPONSE_SCHEMA_EXAMPLE`

환경변수 override를 읽는 로직은 별도 helper로 둔다.

```text
get_it_keyword_int_config(env_key, default)
```

이 helper는 다음 규칙을 따른다.

- 환경변수가 없으면 default를 반환한다.
- 환경변수가 양의 정수이면 해당 값을 반환한다.
- 환경변수가 비어 있거나 양의 정수가 아니면 default를 반환한다.
- 잘못된 환경변수 값 때문에 배치가 중단되지 않는다.

전처리 함수 내부에는 의미 있는 숫자 literal을 직접 두지 않는다. 테스트도 config 값을 기준으로 검증한다.

## Prompt 변경

`build_it_keyword_prompt`는 원문 `content` 대신 검증된 `compressed_content`를 사용한다.

prompt에는 다음 라벨을 사용한다.

```text
[title]
PyTorch 2.5 릴리스

[compressed_content]
추론 성능과 배포 편의성이 개선되었다.

[interest]
view_count=1200, comment_count=8, point=3, interest_score=1340, interest_level=high
```

LLM에는 이 텍스트가 원문 발췌 압축본임을 명시한다. 새 사실을 만들지 말라는 기존 제약은 유지한다.

## 테스트 설계

추가 테스트 범위:

- 짧은 content는 압축해도 원문과 같을 수 있다.
- 긴 content는 `MAX_CONTENT_CHARS` 이하로 줄어든다.
- 압축 결과의 각 unit은 정규화된 원문 안에 존재한다.
- 원문에 없는 문장이 compressed에 들어가면 검증 실패다.
- 긴 원문에서 compressed가 원문보다 짧지 않으면 검증 실패다.
- 단일 긴 문단은 문장 단위로 재분해해 선택한다.
- 검증 실패 row는 LLM 호출 없이 스킵된다.
- 검증 실패 row만 있으면 MERGE를 호출하지 않는다.
- `build_it_keyword_prompt`는 `[compressed_content]`를 포함하고 원문 전체를 그대로 넣지 않는다.
- 환경변수로 max chars/units를 override할 수 있다.
- 전처리 숫자 제한값, prompt 라벨, IT 관점 단어 목록이 `AnalyzeItKeywordsConfig`에 집중되어 있다.
- 잘못된 환경변수 값은 default로 fallback된다.

## 운영 기대 효과

- `gemma4:26b` CPU 실행 환경에서도 긴 IC02 content로 인한 timeout 가능성을 낮춘다.
- LLM 입력은 원문 발췌 기반이므로 전처리 단계에서 새 사실이 섞이지 않는다.
- 검증 실패 row를 스킵하므로 잘못 압축된 입력이 DB keywords로 이어지지 않는다.
- 변경 범위가 IC02 전용 모듈에 머물러 기존 맛집 분석 흐름을 건드리지 않는다.

## 승인 기준

구현 완료 조건:

- 신규 전처리·검증 unit test가 통과한다.
- IC02 orchestration 테스트에서 검증 실패 row 스킵이 확인된다.
- 기존 IC01 감성/BERT 키워드 테스트가 통과한다.
- 전체 `ai/post_analysis` 테스트가 통과한다.
- DB merge payload는 계속 `crawling_id`, `keywords`만 포함한다.
- 전처리 관련 숫자·라벨·scoring terms가 함수 내부에 흩어져 있지 않고 config로 관리된다.
