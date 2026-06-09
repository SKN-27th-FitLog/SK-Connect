# IC02 회사 분류 키워드와 제목 감성 분석 설계

## 목적

IC02 IT 뉴스 후처리에서 오래 걸리는 Ollama 기반 키워드 생성을 제거하고, 조회와 게시글 생성에 필요한 최소 신호만 빠르게 저장한다.

이번 설계는 기존 IC02 키워드 설계의 LLM 요약, 흐름 분석, 12~15개 키워드 생성 요구를 대체한다. IC02는 앞으로 회사명과 회사 분류를 deterministic 방식으로 뽑고, 제목 기반 감성 결과를 기존 `analysis.sentimental` / `analysis.score`에 저장한다.

## 범위

포함한다.

- `ai/post_analysis` 내부에 IC02 회사 사전과 회사 분류 매칭 로직을 둔다.
- IC02 처리에서 Ollama, OpenAI, KAG, Neo4j, PGVector, embedding 경로를 사용하지 않는다.
- IC02 제목을 기존 `BertTokenizer.predict_sentiment(title)`로 분석한다.
- 제목 감성 결과는 기존 `analysis.sentimental`과 `analysis.score`에 저장한다.
- 회사명과 회사 분류는 기존 `analysis.keywords`에 `#` 구분 문자열로 저장한다.
- AWS 운영 비용을 줄이기 위해 row별 성공 로그와 결과 payload 로그를 남기지 않는다.

포함하지 않는다.

- DB 스키마 변경
- 기존 IC01 맛집 감성 분석 규칙 변경
- 기존 IC01 BERT span 키워드 분석 규칙 변경
- `etl/it_news`, `etl/meal`, `ai/postmake_pipeline` 변경
- KAG 그래프 적재 또는 회사 노드 생성
- 실시간 주가, 종목코드, 재무지표, 외부 금융 API 연동

## 기존 설계와의 관계

`docs/superpowers/specs/2026-05-27-ic02-it-keywords-design.md`는 IC02 키워드를 LLM으로 생성하고, 요약/흐름/관심도 신호를 키워드 생성 컨텍스트로 사용하도록 정의했다.

이 설계는 그 중 IC02 키워드 생성 방식과 저장 의미를 다음처럼 변경한다.

- LLM 키워드 생성은 제거한다.
- IC02 키워드는 게시글 관점 키워드가 아니라 회사명과 회사 분류 신호로 제한한다.
- IC02도 기존 감성 스키마를 사용하되, 기존 `analyze_sentimental.py`의 IC02 제외 규칙은 유지한다.
- IC02 제목 감성은 IC02 전용 처리 흐름 안에서만 수행한다.

## 데이터 계약

### 감성 저장

IC02 제목 감성은 기존 컬럼을 사용한다.

```text
analysis.sentimental: "positive" | "negative"
analysis.score: float
```

감성 분석기는 기존 `common.bert_tokenizer.BertTokenizer`를 사용한다.

- 모델명: `AnalyzeSentimentalConfig.MODEL_NAME`
- 현재 기본값: `sangrimlee/bert-base-multilingual-cased-nsmc`
- 입력: `analysis.title`
- 출력: `SentimentResultKey.SENTIMENTAL`, `SentimentResultKey.SCORE`
- 판정 규칙: `positive_score >= negative_score`면 `positive`, 아니면 `negative`

### 키워드 저장

회사명과 회사 분류는 기존 `analysis.keywords`에 저장한다.

```text
#OpenAI#ai_company#NVIDIA#semiconductor
```

저장 규칙은 다음과 같다.

- 회사명과 회사 분류를 한 쌍으로 저장한다.
- 같은 회사가 title/content에 여러 번 등장해도 한 번만 저장한다.
- 회사 사전 순서를 deterministic 우선순위로 사용한다.
- 기존 downstream 호환을 위해 `normalize_it_keywords`의 `#` 구분 형식을 유지한다.
- 회사가 하나도 매칭되지 않으면 `keywords`는 변경하지 않는다.
- `overwrite=True`일 때만 기존 IC02 `keywords`를 새 회사/분류 결과로 덮어쓴다.

## 회사 사전

회사 사전은 `ai/post_analysis` 내부에 둔다. KAG의 `kag_graph.news_classifier`는 재사용하지 않는다.

이유는 다음과 같다.

- 현재 `kag_graph`는 기본 import 경로에 없고 `PYTHONPATH=kag/src`가 필요하다.
- 기존 IC02 설계는 구현 범위를 `ai/post_analysis` 내부로 제한한다.
- 회사명/분류 매칭은 작은 deterministic 사전으로 충분하다.
- AWS batch 이미지에서 KAG/Neo4j 의존성을 빼는 편이 비용과 배포 복잡도를 줄인다.

사전 항목은 명시적 구조를 가진다.

```text
canonical_name: "OpenAI"
company_type: "ai_company"
aliases: ("openai", "chatgpt 개발사")
```

초기 사전은 문서에 정의된 회사만 넣고, 운영 중 발견한 누락 회사는 별도 승인 후 추가한다.

초기 후보:

- OpenAI: `ai_company`
- Anthropic: `ai_company`
- Google: `bigtech`
- Microsoft: `bigtech`
- Apple: `bigtech`
- NVIDIA: `semiconductor`
- Samsung: `semiconductor`

## 처리 흐름

IC02 전용 처리 흐름은 다음 순서로 동작한다.

```text
get_it_keyword_target_data()
-> 필수 컬럼 검증
-> 제목 유효성 검증
-> 회사 사전 매칭(title + content)
-> 제목 감성 분석(title)
-> keywords/sentimental/score 업데이트 payload 구성
-> merge_analysis_data()
```

기존 함수명 `analyze_it_keywords`는 유지한다. 단, 역할은 IC02 LLM 키워드 생성이 아니라 IC02 회사 분류 키워드와 제목 감성 저장으로 바뀐다. 구현 시 docstring과 테스트 이름은 새 역할을 반영한다.

## 대상 row 기준

기본 실행은 다음 IC02 row만 처리한다.

- `information_cd == IC02`
- `title` 또는 `content` 중 하나 이상 유효
- `sentimental` 또는 `score`가 비어 있음

이 기준을 기본값으로 둔다. 회사가 매칭되지 않은 row라도 제목 감성을 저장하면 다음 기본 실행에서 반복 처리되지 않는다.

`overwrite=True`일 때는 유효한 IC02 row를 재처리한다.

- 제목 감성을 다시 계산한다.
- 회사가 매칭되면 `keywords`를 새 회사/분류 결과로 덮어쓴다.
- 회사가 매칭되지 않으면 `keywords`를 비우지 않고 기존 값을 유지한다.

`max_rows`는 `get_it_keyword_target_data()`의 SQL 조회 단계에서 적용한다. 항상 IC02 필터 이후의 상한으로 동작해야 한다.

## 오류 처리

필수 컬럼이 없으면 `ValueError`를 발생시킨다.

제목이 비어 있고 본문도 비어 있으면 처리 대상에서 제외한다.

개별 row 처리 실패는 전체 batch를 중단하지 않는다. 실패 row는 count만 누적하고, 예외 로그는 `ERROR`/`EXCEPTION`으로 남긴다.

모든 row가 실패했거나 저장할 변경분이 없으면 `merge_analysis_data`를 호출하지 않는다.

감성 분석 모델 로드 실패는 batch 전체 실패로 본다. 회사 매칭은 가능하더라도 감성 스키마 저장이 이번 설계의 필수 결과이기 때문이다.

## 로그 정책

AWS 운영에서는 CloudWatch 로그 비용과 노이즈를 줄이기 위해 row별 성공 로그를 남기지 않는다.

`INFO`에는 batch 단위 요약만 남긴다.

- 시작/종료
- target_count
- processed_count
- merged_count
- skipped_count
- failed_count
- positive_count
- negative_count
- company_matched_count
- company_unmatched_count

`WARNING`에는 운영자가 확인해야 하는 비정상 입력 요약만 남긴다.

- 필수는 아니지만 회사 매칭 0건 비율이 과도하게 높은 경우
- 제목이 없어 감성 분석을 수행할 수 없는 row가 많은 경우

`ERROR`/`EXCEPTION`에는 실패 원인을 남긴다.

- DB 조회 실패
- DB merge 실패
- 감성 모델 추론 실패
- row 처리 중 예외

`DEBUG`에만 row별 상세를 허용한다.

- crawling_id
- title
- matched companies
- generated keywords
- sentimental
- score

기본 운영 로그 레벨은 `INFO`다. 필요하면 환경변수로 `DEBUG`를 켤 수 있게 하되, 기본 구현에서 개별 row 결과를 `INFO`로 출력하지 않는다.

## AWS 비용 기준

이번 설계의 비용 절감 원칙은 다음과 같다.

- IC02 처리에서 Ollama/Gemma 서버를 사용하지 않는다.
- IC02 처리에서 OpenAI API를 사용하지 않는다.
- IC02 처리에서 KAG/Neo4j/Neptune을 사용하지 않는다.
- IC02 처리에서 PGVector/embedding을 사용하지 않는다.
- 상시 실행 서버가 아니라 scheduled batch로 실행할 수 있게 유지한다.
- batch는 SQL에서 대상 IC02 row만 읽고, 변경 row만 merge한다.

AWS 배포 시 권장 실행 형태는 EventBridge Scheduler가 ECS/Fargate task를 짧게 실행하는 방식이다. `torch`와 `transformers` 모델 로드가 필요하므로 Lambda는 기본 권장 대상이 아니다.

## 테스트 기준

추가 또는 수정할 테스트는 실제 DB, Hugging Face Hub, 외부 LLM을 호출하지 않는다.

필수 테스트:

- 회사 사전 매칭이 alias와 대소문자를 처리한다.
- 회사명과 회사 분류가 `#회사명#회사분류` 순서로 저장된다.
- 중복 회사는 한 번만 저장된다.
- 회사가 매칭되지 않으면 기존 keywords를 비우지 않는다.
- IC02 제목을 `BertTokenizer.predict_sentiment(title)`에 전달한다.
- 감성 결과가 `analysis.sentimental`과 `analysis.score`에 반영된다.
- 기본 실행은 IC02 중 `sentimental` 또는 `score`가 비어 있는 row만 처리한다.
- `overwrite=True`는 유효 IC02 row를 재처리한다.
- row별 성공 로그를 `INFO`로 남기지 않는다.
- batch summary 로그는 count 중심으로 남긴다.
- 기존 IC01 `analyze_sentimental`의 IC02 제외 테스트는 유지된다.
- 기존 IC01 키워드 테스트는 유지된다.

## 승인 기준

구현은 다음을 만족해야 완료로 본다.

- IC02 처리에서 Ollama 호출 경로가 제거된다.
- IC02 처리에서 회사명과 회사 분류만 `analysis.keywords`에 저장된다.
- IC02 제목 감성이 기존 `analysis.sentimental` / `analysis.score`에 저장된다.
- DB 스키마 변경이 없다.
- 기존 IC01 감성/키워드 처리 계약이 깨지지 않는다.
- 관련 `post_analysis` 단위 테스트가 통과한다.
- 검증 결과에는 Root Cause, Change, Verification, Remaining Risk가 포함된다.
