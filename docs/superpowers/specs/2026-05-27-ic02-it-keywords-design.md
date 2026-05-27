# IC02 IT 전용 키워드 분석 설계

## 목적

`post_analysis`에 IC02 IT 뉴스 전용 키워드 분석 단계를 추가한다.
기존 IC01 맛집 리뷰 감성 분석과 BERT span 키워드 분석은 변경하지 않는다.

현재 IT 뉴스는 `etl/it_news`에서 `crawling`으로 적재될 때 `category_cd=CA07`, `information_cd=IC02`로 들어온다. 그러나 `etl/it_news` 크롤러는 `keywords`를 생성하지 않고, `post_analysis`의 기존 감성/키워드 단계는 IC02를 제외한다. 그 결과 IC02 row는 `analysis.keywords`가 비어 있을 수 있고, `postmake_pipeline`의 `usable_analysis` 조건에서 제외될 수 있다.

## 범위

포함한다.

- `post_analysis` 내부에 IC02 전용 키워드 분석 모듈을 추가한다.
- 기본 실행은 `analysis.keywords`가 NULL 또는 빈 문자열인 IC02 row만 처리한다.
- 명시 옵션으로 기존 IC02 keywords 재생성을 허용한다.
- 결과는 기존 downstream 계약과 동일하게 `analysis.keywords`에 `#` 구분 문자열로 저장한다.
- `pipeline.py`에서 기존 3단계 뒤에 IC02 전용 단계를 추가한다.

포함하지 않는다.

- IC01 맛집 감성 분석 로직 변경
- IC01 맛집 BERT 키워드 분석 로직 변경
- `etl/it_news` 크롤링/클리닝/save 로직 변경
- `postmake_pipeline`의 게시글 생성 로직 변경
- DB 스키마 변경

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

## 모듈 설계

새 모듈 `ai/post_analysis/analyze_it_keywords.py`를 추가한다.

주요 함수는 `analyze_it_keywords(max_rows: int | None = None, overwrite: bool = False) -> None`로 둔다.

처리 조건은 다음과 같다.

- 필수 컬럼: `title`, `content`, `keywords`, `information_cd`, `crawling_id`
- `information_cd == IC02`
- `title` 또는 `content` 중 하나 이상이 유효한 문자열
- `overwrite=False`: `keywords`가 NULL 또는 공백 문자열인 row만 처리
- `overwrite=True`: 유효한 IC02 row를 재처리
- `max_rows`가 양의 정수면 필터 이후 상위 N건만 처리

키워드 생성은 별도 순수 함수로 분리한다.

- `build_it_keyword_input(row)`: title/content를 모델 입력 문자열로 정리
- `normalize_it_keywords(value)`: 모델 출력 또는 후보 문자열을 기존 `#keyword` 형식으로 정규화
- `extract_it_keywords(...)`: LLM 호출을 감싼 추출 함수

LLM 응답은 신규 Pydantic 모델로 검증한다. 필드는 `keywords: list[str]`로 고정한다. 각 항목은 공백 제거 후 빈 문자열을 제외하고, 중복 제거 후 최대 7개까지 유지한다. 최종 DB 저장 직전에는 항상 `#` 구분 문자열로 정규화한다.

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
- LLM 결과가 `#` 구분 문자열로 정규화된다.
- row 단위 실패는 계속 진행하고 성공분만 merge한다.
- `pipeline.run_pipeline`이 기존 3단계 이후 IC02 단계를 호출한다.

## 운영 기본값

운영 기본값은 보수적으로 둔다.

- 기본 실행은 비어 있는 IC02 keywords만 채운다.
- 기존 IC02 keywords 재생성은 `--overwrite-it-keywords`를 명시해야 한다.
- 기존 IC01 맛집 파이프라인의 동작과 결과는 변경하지 않는다.

## 승인 기준

구현은 다음을 만족해야 완료로 본다.

- 기존 IC01 관련 테스트가 통과한다.
- 신규 IC02 키워드 테스트가 통과한다.
- `post_analysis` 테스트의 MERGE 차단 규칙을 위반하지 않는다.
- `analysis.keywords` 저장 형식이 `postmake_pipeline.common.text_utils.parse_keywords`와 호환된다.
- 문서와 코드에서 IC01/IC02 책임 경계가 명확하다.
