# IC02 IT 전용 키워드 분석 설계

## 목적

`post_analysis`에 IC02 IT 뉴스 전용 키워드 분석 단계를 추가한다.
기존 IC01 맛집 리뷰 감성 분석과 BERT span 키워드 분석은 변경하지 않는다.

현재 IT 뉴스는 `etl/it_news`에서 `crawling`으로 적재될 때 `category_cd=CA07`, `information_cd=IC02`로 들어온다. 그러나 `etl/it_news` 크롤러는 `keywords`를 생성하지 않고, `post_analysis`의 기존 감성/키워드 단계는 IC02를 제외한다. 그 결과 IC02 row는 `analysis.keywords`가 비어 있을 수 있고, `postmake_pipeline`의 `usable_analysis` 조건에서 제외될 수 있다.

## 범위

포함한다.

- `post_analysis` 내부에 IC02 전용 키워드 분석 모듈을 추가한다.
- `post_analysis` 내부에서도 IC02 키워드 추출과 `analysis.keywords` 반영 경로만 수정한다.
- 기본 실행은 `analysis.keywords`가 NULL 또는 빈 문자열인 IC02 row만 처리한다.
- 명시 옵션으로 기존 IC02 keywords 재생성을 허용한다.
- 요약, 글의 흐름, 관심도 신호를 키워드 생성 컨텍스트로 사용한다.
- 결과는 기존 downstream 계약과 동일하게 `analysis.keywords`에 `#` 구분 문자열로 저장한다.
- `pipeline.py`에서 기존 3단계 뒤에 IC02 전용 단계를 추가한다.

포함하지 않는다.

- IC01 맛집 감성 분석 로직 변경
- IC01 맛집 BERT 키워드 분석 로직 변경
- `etl/it_news` 크롤링/클리닝/save 로직 변경
- `postmake_pipeline`의 게시글 생성 로직 변경
- DB 스키마 변경
- IC01 처리를 위해 존재하는 기존 함수의 동작 변경

## 범위 보호 원칙

구현은 `ai/post_analysis` 폴더 안에서만 진행한다. 그 안에서도 변경 대상은 IC02 IT 뉴스 키워드를 뽑고 `analysis.keywords`로 전달하는 코드로 제한한다.

다음 영역은 명시적으로 수정하지 않는다.

- `get_reviews`의 기존 IC01 shop 매칭 규칙
- `analyze_sentimental`의 기존 IC01 감성 분석 규칙
- `analyze_keywords`의 기존 IC01 BERT 키워드 추출 규칙
- `etl/meal`, `etl/it_news`, `ai/postmake_pipeline`
- DB 스키마와 기존 MERGE SQL 컬럼 계약

기존 파일을 수정해야 할 경우는 `pipeline.py`에 IC02 전용 단계를 연결하거나 공통 상수/오류 메시지에 IC02 전용 항목을 추가하는 경우로 제한한다. 이때도 기존 IC01 함수의 필터, 입력, 출력, 저장 동작은 변경하지 않는다.

## 현재 연결 계약

`post_analysis.get_reviews`는 신규 `crawling` row를 `analysis`로 적재한다. `category_cd=CA07` row는 `information_cd=IC02`로 분류되고, shop 매칭은 생략된다.

기존 `analyze_sentimental`과 `analyze_keywords`는 `information_cd != IC02`만 처리한다. 이 규칙은 유지한다.

`postmake_pipeline.get_data`는 `analysis.keywords`를 우선 사용하고, 없으면 `crawling.keywords`를 사용한다. 둘 다 없으면 `keywords IS NOT NULL` 조건을 통과하지 못한다. 따라서 IC02 전용 분석은 `analysis.keywords`를 채워 downstream 진입 조건을 만족시키는 역할을 한다.

## 키워드 의미

IC02 키워드는 맛집 리뷰 감정 키워드가 아니라, IT 뉴스 게시글 생성을 위한 신호다.

추출 결과는 두 성격을 함께 포함해야 한다.

- 기술 주제: 기술명, 제품명, 회사명, 프레임워크, 보안 이슈, 릴리스명
- 게시글 관점: 변화점, 영향, 장점, 리스크, 활용 포인트, 개발자에게 중요한 맥락

예시 형식:

```text
#PyTorch#모델 최적화#추론 속도 개선#GPU 비용 절감#개발 생산성
```

## 요약·흐름·관심도 신호

IC02 전용 분석은 단순 명사 추출이 아니라 게시글 생성에 필요한 관점을 만들어야 한다. 이를 위해 LLM 입력에는 원문과 함께 다음 신호를 포함한다.

- 요약: 글이 말하는 핵심 변화나 발표 내용을 짧게 정리한다.
- 흐름: 문제 제기, 변경 사항, 영향, 주의점처럼 글의 전개 구조를 파악한다.
- 관심도: `crawling.view_count`, `crawling.comment_count`, `crawling.point`를 이용해 독자 반응 신호를 계산한다.

관심도는 DB에 별도 저장하지 않는다. IC02 키워드 생성 시 우선순위를 조정하는 내부 신호로만 사용한다. 예를 들어 조회수와 댓글이 높은 글은 `높은 커뮤니티 관심`, `논의 확산`, `개발자 반응` 같은 게시글 관점 키워드가 후보에 포함될 수 있다.

관심도 등급은 deterministic helper에서 계산한다. 기본 등급은 `high`, `medium`, `low` 세 단계로 둔다.

초기 관심도 점수는 다음 공식으로 계산한다.

```text
interest_score = view_count + comment_count * 10 + max(point, 0) * 20
```

등급 기준은 다음과 같다.

- `high`: `interest_score >= 1000`
- `medium`: `interest_score >= 100`
- `low`: 그 외

NULL 또는 변환 불가능한 메트릭은 0으로 처리한다. 공식의 가중치와 임계값은 `AnalyzeItKeywordsConfig`에 둬 테스트 가능하게 한다.

## LLM 모델 선택

IC02 전용 분석의 기본 LLM provider는 Ollama로 둔다.

기본 모델은 `gemma4:26b`로 확정한다. 이 모델은 요약, 흐름 파악, 관심도 신호를 종합한 키워드 추출에 사용한다.

모델명은 코드에 직접 하드코딩하지 않고 IC02 전용 설정 상수로 둔다. 기본값은 `gemma4:26b`이며, 환경변수로 override할 수 있게 한다.

OpenAI 기반 기존 `analyze_keywords_by_llm.py`는 IC01 맛집 리뷰 실험용 흐름이므로 재사용하지 않는다. IC02 전용 모듈은 Ollama 호출 경로와 응답 검증 모델을 별도로 가진다.

## 모듈 설계

새 모듈 `ai/post_analysis/analyze_it_keywords.py`를 추가한다.

주요 함수는 `analyze_it_keywords(max_rows: int | None = None, overwrite: bool = False) -> None`로 둔다.

처리 조건은 다음과 같다.

- 필수 컬럼: `title`, `content`, `keywords`, `information_cd`, `crawling_id`
- 선택 컨텍스트 컬럼: `view_count`, `comment_count`, `point`
- `information_cd == IC02`
- `title` 또는 `content` 중 하나 이상이 유효한 문자열
- `overwrite=False`: `keywords`가 NULL 또는 공백 문자열인 row만 처리
- `overwrite=True`: 유효한 IC02 row를 재처리
- `max_rows`가 양의 정수면 필터 이후 상위 N건만 처리

IC02 분석 입력은 `analysis`를 기준으로 만들고, `crawling_id`가 같은 `crawling` row의 `view_count`, `comment_count`, `point`를 함께 읽는다. 메트릭이 없으면 0 또는 `None`으로 정규화해 분석을 계속한다.

키워드 생성은 별도 순수 함수로 분리한다.

- `build_it_keyword_input(row)`: title/content를 모델 입력 문자열로 정리
- `compute_interest_signal(row)`: view/comment/point 기반 관심도 등급과 설명을 계산
- `normalize_it_keywords(value)`: 모델 출력 또는 후보 문자열을 기존 `#keyword` 형식으로 정규화
- `extract_it_keywords(...)`: LLM 호출을 감싼 추출 함수

LLM 응답은 신규 Pydantic 모델로 검증한다. 필드는 `summary: str`, `flow: str`, `interest_label: str`, `keywords: list[str]`로 고정한다. `summary`, `flow`, `interest_label`은 DB에 저장하지 않고 row 처리 로그와 키워드 품질 검증용 구조로만 사용한다. `keywords` 각 항목은 공백 제거 후 빈 문자열을 제외하고, 중복 제거 후 최대 7개까지 유지한다. 최종 DB 저장 직전에는 항상 `#` 구분 문자열로 정규화한다.

기존 `analyze_keywords_by_llm.Keywords`는 맛집 리뷰 감성 기반 LLM 실험용 스키마이므로 재사용하지 않는다. IC02 전용 모듈은 별도 응답 모델을 가져야 한다.

## 파이프라인 설계

`ai/post_analysis/pipeline.py`는 기존 순서를 유지하고 마지막에 IC02 전용 단계를 추가한다.

```text
get_reviews
→ analyze_sentimental
→ analyze_keywords
→ analyze_it_keywords
```

기존 `--max-rows`는 기존 IC01 키워드 단계에 전달한다.

신규 CLI 옵션은 다음과 같다.

- `--it-keywords-max-rows`: IC02 전용 키워드 분석 상한
- `--overwrite-it-keywords`: IC02 keywords 기존값 재생성

이름을 분리해 IC01 키워드 배치와 IC02 키워드 배치의 실행 제어를 명확히 한다.

## 오류 처리

필수 컬럼이 없으면 `ValueError`를 발생시킨다.

처리 대상이 없으면 info 로그를 남기고 종료한다.

개별 row의 LLM 호출 또는 파싱 실패는 로그를 남기고 다음 row로 진행한다. 성공한 row만 `merge_analysis_data`로 반영한다.

모든 row가 실패해 저장할 keywords가 없으면 MERGE를 호출하지 않는다.

## 테스트 설계

기본 테스트는 실제 DB MERGE와 외부 LLM 호출을 하지 않는다.

추가할 테스트 범위:

- IC02만 처리하고 IC01은 제외한다.
- `overwrite=False`일 때 NULL/공백 keywords만 처리한다.
- `overwrite=True`일 때 기존 keywords가 있는 IC02도 처리한다.
- `title`만 있거나 `content`만 있어도 처리한다.
- `max_rows`가 필터 후 상한으로 적용된다.
- `view_count`, `comment_count`, `point`가 관심도 신호로 정규화된다.
- 관심도 메트릭이 없거나 NULL이어도 IC02 키워드 분석은 중단되지 않는다.
- Ollama LLM factory가 기본 모델명 `gemma4:26b`를 사용하고 환경변수 override를 허용한다.
- LLM 응답의 `summary`, `flow`, `interest_label`, `keywords` 구조를 검증한다.
- LLM 결과가 `#` 구분 문자열로 정규화된다.
- row 단위 실패는 계속 진행하고 성공분만 merge한다.
- `pipeline.run_pipeline`이 기존 3단계 이후 IC02 단계를 호출한다.

## 운영 기본값

운영 기본값은 보수적으로 둔다.

- 기본 실행은 비어 있는 IC02 keywords만 채운다.
- 기존 IC02 keywords 재생성은 `--overwrite-it-keywords`를 명시해야 한다.
- IC02 기본 모델은 Ollama `gemma4:26b`다.
- 기존 IC01 맛집 파이프라인의 동작과 결과는 변경하지 않는다.

## 승인 기준

구현은 다음을 만족해야 완료로 본다.

- 기존 IC01 관련 테스트가 통과한다.
- 신규 IC02 키워드 테스트가 통과한다.
- `post_analysis` 테스트의 MERGE 차단 규칙을 위반하지 않는다.
- `analysis.keywords` 저장 형식이 `postmake_pipeline.common.text_utils.parse_keywords`와 호환된다.
- IC02 키워드 분석은 요약, 흐름, 관심도 신호를 입력 컨텍스트로 사용한다.
- 문서와 코드에서 IC01/IC02 책임 경계가 명확하다.
