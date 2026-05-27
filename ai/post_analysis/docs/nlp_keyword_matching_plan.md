# NLP 키워드 매칭 진행 기록

## 1차 목표 (mockup) — 완료

리뷰 본문과 LLM으로 만든 키워드 샘플 간 **의미 유사도**를 계산해, 조건을 만족하는 상위 키워드를 CSV에 반환한다.

| 항목 | 내용 |
|------|------|
| 입력 | `data/review_test_input.csv.csv` (164건, `content`, `sentimental`) |
| 키워드 풀 | `data/keyword_matching_samples.csv` |
| 후보 필터 | `use_for_matching == true` **且** `sentiment_label == sentimental` |
| 유사도 | 코사인 유사도 ≥ **0.7** |
| 출력 개수 | 상위 **3개** (미달 시 있는 만큼, 0건이면 빈 문자열) |
| 출력 형식 | `#키워드1#키워드2#키워드3` (LLM 파이프라인과 동일) |
| 코드 | `common/nlp_keywords.py` |

## 구현 요약

- **모델**: `jhgan/ko-sroberta-multitask` (`sentence-transformers`)
- **비교 텍스트**: 리뷰 `content` ↔ 키워드 `masked_keyword`
- **최적화**: sentimental별 키워드 임베딩·리뷰 본문 임베딩을 각각 배치로 1회 계산
- **의존성**: `requirements.txt`에 `sentence-transformers>=3.0.0` 추가, `.venv`에서 설치

## 실행 방법

```powershell
cd c:\dev\project\SK-Connect\ai\post_analysis
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt   # 최초 1회
python -m common.nlp_keywords
```

실행 시 `data/review_test_input.csv.csv`의 `keywords` 컬럼이 **같은 파일**에 덮어쓰기 된다.

## 1차 실행 결과 (2026-05-27)

| 지표 | 값 |
|------|-----|
| 전체 행 | 164 |
| keywords 채워진 행 | **63** |
| 미매칭(빈 문자열) | **101** |
| positive 키워드 후보 | 278건 |
| negative 키워드 후보 | 40건 |

### 샘플 (crawling_id 기준)

| crawling_id | sentimental | content (앞 50자) | keywords |
|-------------|-------------|-------------------|----------|
| 349 | positive | 반찬도 맛있고 오징어 볶음이 진짜 맛있어요 또 밥 한그릇… | `#오징어볶음 정말 맛있습니다#맛있고 오징어 볶음#오징어 양념도 맛있어요` |
| 350 | positive | 강릉의 작은 식당인데 방문객도 많고 맛도 좋고 가성비도… | *(미매칭 — 빈 값)* |
| 351 | positive | 갈치조림 그렇게 안 좋아하는데 진짜 맛있게 먹었습니다… | `#갈치조림이 맛있음` |
| 353 | positive | 정감가득한 식당입니다 동네맛집인지 점심에 사람… | `#오징어볶음 정말 맛있습니다#맛있고 오징어 볶음#오징어 양념도 맛있어요` |
| 363 | positive | 오징어 양념도 맛있어요!! 메뉴가 간단한데… | `#오징어 양념도 맛있어요#맛있고 오징어 볶음#오징어볶음 정말 맛있습니다` |

crawling_id 349는 ground truth(오징어·맛 관련)와 일치하는 키워드가 상위에 포함되었다.

## 관찰

1. **0.7 임계값이 높음**: 164건 중 101건(61%)이 미매칭. 짧은 리뷰(예: 350)는 전체 본문 임베딩과 짧은 키워드 문구 간 유사도가 0.7에 못 미치는 경우가 많다.
2. **긴 리뷰 vs 짧은 키워드**: 현재는 리뷰 **전체** `content`와 키워드 1문장을 비교한다. 문장 분할·span 매칭 없이는 “리뷰 일부”에 해당하는 키워드를 놓치기 쉽다.
3. **sentiment 필터**: positive/negative 키워드 풀이 분리되어 부정 리뷰에 긍정 키워드가 섞이지 않는다 (negative 후보 40건으로 상대적으로 적음).
4. **NaN 처리**: `content` NaN은 빈 문자열로 치환 후 임베딩 (실행 중 발견·수정).

## 다음 단계 (2차 이후)

- PostgreSQL `analysis` 테이블 MERGE 연동
- `pipeline.py` 오케스트레이션 편입
- Level 0 단위 테스트 (`_slide_spans`, `_span_target_score` 등)

---

## 2~3차 실험 이력 (요약)

| 단계 | 방식 | 코드 | 비고 |
|------|------|------|------|
| 2차 | Kiwi 3형태소 sliding | `bert_keywords.py` (구버전) | 형태소 fragment (`#맛있 어요`) |
| 3차 | 공백 2~3어절 + greedy 비중복 | `bert_keywords2.py` | 원문 어절 보존, 혼합 감성 span 잔존 |
| **통합** | 전처리 + 2~3어절 + 필터 4종 | **`bert_keywords.py` (최종)** | 2·3차 장점 합침, `bert_keywords2.py`는 re-export만 |

---

## 최종 통합 (BERT span keywords) — `common/bert_keywords.py`

원문 `content`를 **전처리 후 공백 split** → **2~3어절 sliding** 후보 → BERT 감성 점수 → 후처리 필터 → **비중복 greedy top 3**을 `#`로 연결한다.

| 항목 | 내용 |
|------|------|
| 입력 | `data/review_test_input.csv.csv` (`content`, `sentimental`) |
| 전처리 | `.`→공백, 특수문자→공백, 연속 공백 축소, 자음·모음 단독 어절(ㅠ 등) 제거 |
| 후보 생성 | 전처리 `split` → **2·3어절** 윈도우, stride=1 |
| 점수 | `BertTokenizer.predict_sentiment` — label==`sentimental`일 때만 해당 방향 score |
| subspan dominance | 긴 span 점수 ≥ 짧은 subspan − **0.05** 이면 **짧은** subspan 제거 (3어절 우선) |
| 혼합 감성 필터 | span 내 **감성형 어절**만 단독 BERT 검사 — 반대 label이고 (score ≥ **0.5** 且 margin ≥ **0.025**) 또는 score ≥ **0.55** 이면 span 제외 |
| 선택 | 점수 내림차순 **greedy 비중복** top 3 (동점 시 **긴 span** 우선) |
| 출력 형식 | `#span1#span2#span3` |
| 코드 | **`common/bert_keywords.py`** (`bert_keywords2.py`는 deprecated re-export) |

### 실행 방법

```powershell
cd c:\dev\project\SK-Connect\ai\post_analysis
.\.venv\Scripts\Activate.ps1
python -m common.bert_keywords
```

실행 시 `data/review_test_input.csv.csv`의 `keywords` 컬럼이 **같은 파일**에 덮어쓰기 된다.

### 통합 실행 결과 (2026-05-25)

| 지표 | 1차 (샘플 유사도) | 통합 (BERT span) |
|------|-------------------|------------------|
| 전체 행 | 164 | 164 |
| keywords 채워진 행 | 63 | **151** |
| 미매칭(빈 문자열) | 101 | **13** |
| 실행 시간 | ~수 초 | **~4.6분** (164건, span별 BERT 순차 호출) |

### 샘플 (crawling_id 기준)

| crawling_id | sentimental | keywords (통합) | 메모 |
|-------------|-------------|-----------------|------|
| 349 | positive | `#반찬도 맛있고#진짜 맛있어요 또#먹으러 가고싶네욤` | 3어절 `#진짜 맛있어요 또` 우선 |
| 395 | positive | `#진짜 맛있게 먹었는데#된장찌개 굳` | 3어절 우선 + `아쉽네요` 혼합 span 제거 |
| 427 | positive | `#깻잎지가 정말 맛있었습니다#무난히 좋아할 맛입니다` | 3어절 원문 근거 |

395번: `#아쉽네요 된장찌개 굳`(혼합 3어절) 제거 → `#진짜 맛있게 먹었는데`(3어절) + `#된장찌개 굳`(2어절).

### 통합 관찰

1. **원문 보전**: Kiwi 형태소 join 없이 전처리된 연속 어절 span.
2. **3어절 우선**: subspan dominance·greedy tie-break 모두 긴 span 보호.
3. **혼합 감성**: 감성형 어절(`아쉽네요` 등) 반대 label + margin/score 기준으로 span 제외; 명사형 어절(`된장찌개`)은 필터 대상 아님.
4. **미매칭 13건**: 어절 &lt; 2 (붙여쓴 리뷰) 또는 BERT label 불일치.
5. **속도**: span·단어 BERT 순차 호출 (~수 분 / 164건).

### 다음 단계

- 붙여쓴 리뷰 fallback (Kiwi 또는 LLM)
- `_spans_overlap`·`_suppress_dominated_spans` Level 0 pytest
- ~~품질 확정 후 pipeline·DB MERGE 연동~~ → **4차 완료**

---

## 4차 (DB·pipeline 통합) — 완료

BERT span 키워드 추출을 `analysis` 테이블 MERGE 및 `pipeline.py` 3단계에 연동했다.

| 항목 | 내용 |
|------|------|
| 배치 진입 | `analyze_keywords.py` — `analyze_keywords(max_rows=None)` |
| 추출 엔진 | `common/bert_keywords.py` — `extract_keywords()` |
| 데이터 소스 | `get_analysis_data()` → `merge_analysis_data()` |
| 필터 | IC02 제외, 빈 content 제외, `keywords` 결측만, `sentimental` 결측 제외 |
| pipeline 3단계 | `analyze_keywords_by_llm` → **`analyze_keywords`** |
| LLM 스크립트 | `analyze_keywords_by_llm.py` **유지** (수동·비교 실행용) |

### 실행 방법

```powershell
cd c:\dev\project\SK-Connect\ai\post_analysis
.\.venv\Scripts\Activate.ps1

# 3단계만
python analyze_keywords.py

# 전체 파이프라인 (청크 테스트)
python pipeline.py --max-rows 5
```

### 테스트

```powershell
pytest tests/unit/test_l3_run_pipeline_indirect.py tests/unit/test_l3_analyze_keywords_bert_indirect.py -q
```

- PA-L2-PLN-002/003: pipeline 3단계 순서·`max_rows` 전달
- PA-L3-KW-002/006: pending 0건 스킵, merge에 keywords 반영

### 관찰

1. **레이어 분리**: DB·필터는 `analyze_keywords.py`, span 알고리즘은 `bert_keywords.py`.
2. **2단계 선행**: `sentimental` 없는 행은 3단계에서 자동 제외.
3. **Singleton**: `BertTokenizer`는 감성(2단계)·키워드(3단계) 연속 실행 시 1회 로드.
4. **속도**: mock CSV 기준 ~4.6분/164건과 동일 — 운영 시 `max_rows` 청크 권장.

### 다음 단계 (5차 이후)

- span BERT 배치화 등 성능 개선
- `nlp_keywords.py` (샘플 유사도 매칭) 실험과 BERT span 품질 비교
- `design.md` / function-inventory 스냅샷 갱신

