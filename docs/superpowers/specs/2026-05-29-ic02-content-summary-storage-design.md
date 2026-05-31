# IC02 Content 요약 저장 설계

## 목적

IC02 IT 뉴스 키워드 추출 결과를 사람이 DB에서 확인할 때 원문과 요약을 함께 볼 수 있도록 `analysis.content`에 요약을 추가한다.

DB 스키마는 변경하지 않는다. 새 컬럼을 만들지 않고 기존 `analysis.content`만 사용한다.

## 범위

포함한다.

- `ai/post_analysis/analyze_it_keywords.py` 내부 IC02 처리만 변경한다.
- IC02 키워드 추출이 성공한 row에 한해 `analysis.content`를 아래 형식으로 저장한다.
- 재실행 시 `[요약]` 블록이 중복으로 붙지 않도록 한다.
- 기존 `keywords` 저장은 유지한다.

포함하지 않는다.

- DB 스키마 변경
- `etl/it_news` 크롤링, 클리닝, save 로직 변경
- IC01 감성 분석 및 BERT 키워드 추출 변경
- `ai/postmake_pipeline` 게시글 생성 변경
- 원본 `crawling.content` 변경

## 저장 형식

`analysis.content`는 다음 형식으로 저장한다.

```text
[본문]
원래 analysis.content 본문

[요약]
LLM 응답의 summary
```

`summary`는 기존 `ItKeywordResult.summary` 값을 사용한다. 별도 요약 LLM 호출은 추가하지 않는다.

## 데이터 흐름

```text
analysis row
-> preprocess_it_content
-> extract_it_keywords
-> ItKeywordResult(summary, flow, interest_label, keywords)
-> keywords normalize
-> content enrichment
-> merge_analysis_data(crawling_id, content, keywords)
```

기존 IC02 키워드 추출 LLM 응답에 이미 `summary`가 포함되어 있으므로, 키워드 추출 성공 row에서만 content를 갱신한다.

## 중복 방지

`analysis.content`가 이미 `[본문]`과 `[요약]` 블록을 가진 경우, 기존 블록을 해석해 원문 본문만 다시 사용한다.

규칙:

- content가 `[본문]`으로 시작하고 `[요약]` 블록을 포함하면 `[본문]`과 `[요약]` 사이를 원문 본문으로 본다.
- content가 기존 형식이 아니면 전체 content를 원문 본문으로 본다.
- 새 요약 저장 시 항상 표준 형식으로 다시 만든다.

이 규칙으로 같은 row를 재실행해도 `[요약]` 블록이 누적되지 않는다.

## 빈 본문 처리

content가 비어 있는 row는 기존처럼 키워드 추출 대상에서 실패하거나 skip된다.

이 변경은 빈 content를 title로 대체하지 않는다. 이유는 원문 본문이 없는 row에 `[본문]`을 임의 생성하면 데이터 출처가 불명확해지기 때문이다.

## Merge 범위 변경

기존 IC02 키워드 설계는 DB merge payload를 `crawling_id`, `keywords`로 제한했다.

이번 변경에서는 IC02 content 요약 저장을 위해 성공 row에 한해 `crawling_id`, `content`, `keywords`를 merge한다.

이 예외는 `analyze_it_keywords.py` 내부 IC02 성공 row에만 적용한다. 다른 분석 단계의 merge payload는 변경하지 않는다.

## 에러 처리

- summary가 비어 있으면 content는 갱신하지 않고 keywords만 저장한다.
- content enrichment 중 예외가 발생하면 해당 row는 keywords 저장도 함께 skip한다.
- row 단위 예외 처리는 기존처럼 로그를 남기고 다음 row로 진행한다.

## 테스트 기준

추가 테스트는 다음을 확인한다.

- 일반 content와 summary를 받아 `[본문]`, `[요약]` 형식으로 저장 문자열을 만든다.
- 이미 `[본문]`, `[요약]`이 있는 content를 다시 처리해도 요약 블록이 중복되지 않는다.
- summary가 비어 있으면 content 갱신 대상이 되지 않는다.
- `analyze_it_keywords` 성공 row merge payload에 `content`와 `keywords`가 포함된다.
- IC01 관련 테스트는 기존 동작을 유지한다.

## 승인 기준

- IC02 키워드 추출 성공 row의 `analysis.content`가 표준 형식으로 갱신된다.
- `analysis.keywords`는 기존 `#keyword` 포맷을 유지한다.
- DB 스키마 변경이 없다.
- 게시글 생성 파이프라인은 실행하거나 변경하지 않는다.
