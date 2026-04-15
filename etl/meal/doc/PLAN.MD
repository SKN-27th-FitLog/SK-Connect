# 통합 맛집 데이터 ETL 프로젝트 상세 실행 계획 (PLAN.MD)

본 문서는 `c:\dev\Study\meal` 프로젝트의 전체 구조, 동작 원리 및 향후 검증 로직 추가를 위한 종합 가이드라인입니다. 누구나 쉽게 이해할 수 있도록 실제 코드베이스를 기반으로 꼼꼼하게 정리하였습니다.

---

## 1. 프로젝트 전체 흐름 (Overall Workflow)

이 프로젝트는 **식당 정보 수집 → 위경도 보정 → 리뷰 및 이미지 수집 → DB 저장**의 4단계로 구성된 파이프라인입니다. `run_batch_pipeline.py`가 지휘자 역할을 하여 모든 과정을 순차적으로 실행합니다.

---

## 2. 파일별 상세 기능 및 구현 방식 (Component Deep-dive)

### [Part 1] 맛집 상세 정보 파이프라인 (`meal_detail/`)

#### 1-1. 링크 수집: `01_collect_store_links.py` [Legacy]
- 다이닝코드 검색 목록에서 상세 페이지 URL 수집. (현재 `raw/collect_links.py`로 대체됨)

#### 1-2. 상세 정보 추출: `02_collect_store_details.py` [Legacy]
- 메뉴, 가격, 평정 등 상세 데이터 추출. (현재 `raw/collect_details.py`로 대체됨)

#### 1-3. 전처리 및 업로드: `03_preprocess_and_upload.py` [Legacy]
- `[x]` **상수 Enum 적용**: Category, FoodCategory, Location Enum 도입 완료.
- `[x]` **공통 유틸리티 적용**: `common_utils` 통합 완료.

---

## 3. [전략적 설계] 데이터 정합성 및 고도화 전략 (완료)

- `[x]` **중복 방지**: 가게(좌표/정규화), 메뉴, 리뷰(해시) 중복 체크 구현 완료.
- `[x]` **트랜잭션**: 모든 업로드 과정에 원자성 보장(`ROLLBACK`) 적용 완료.
- `[x]` **아카이빙**: 성공 시 `archives/` 폴더 이동 보존 정책 적용 완료.

---

## 4. [추가] 코드 재사용성 및 구조 개선 (Refactoring)
- `[x]` **공통 유틸리티 모듈(`common_utils.py`) 생성**: 중복 로직 통합 관리 완료.
- `[x]` **기존 스크립트 리팩토링**: `03` 계열 스크립트 유틸리티 적용 완료.

---

## 5. [추가] 상수 관리 효율화 (members.py & Enum)
- `[x]` **상수 관리 파일(`members.py`) 생성**: 시스템 코드 Enum 구조화 완료.
-     - `Status`, `PostType`, `Category`, `FoodCategory`, `Location`, `TablePrefix`
- `[x]` **기존 스크립트 상수 치환**:
-     - `[x]` `meal_detail/03_preprocess_and_upload.py` 적용 완료
-     - `[x]` `meal_review/03_preprocess_and_upload_reviews.py` 적용 완료
-     - `[x]` `common_utils.py` 적용 완료

---

## 6. 실행 및 환경 가이드

- **전체 배치 실행**: `python run_batch_pipeline.py --targets targets_example.csv --headful`

---

## 7. [긴급] 리뷰 데이터 매핑 정합성 해결 (Fix: Review Address Mapping)
- **현상**: 수집된 509건 중 3건만 업로드됨 (주소 불일치로 인한 매핑 실패).
- **원인**: CSV의 전체 주소(Full Address)와 DB의 상세 주소(Detail Address)를 직접 비교하여 매핑이 누락됨.
- **해결 방안 (차세대 검증 파이프라인에서 처리 예정)**: 
    - [ ] **Address Detail Suffix Match**: DB의 상세 주소가 CSV의 전체 주소 끝부분에 포함되어 있는지 확인하는 유연한 매핑 로직 도입.
    - [ ] **Store Name Normalization**: 가게 이름에서 특수문자 및 공백을 제거하여 정합성 강화.

---

## 8. [향후] 데이터 보관 및 보안 정책 (Data Retention & Security)
- [ ] **Git 추적 제외**: `data/`, `review_data/` 등 수집 데이터 및 개인정보가 포함된 파일이 Git 저장소에 올라가지 않도록 `.gitignore` 설정 강화.
- [x] **자동 삭제(Auto-Cleanup)**: DB 업로드 성공 시 로컬 JSON 및 임시 CSV 파일을 삭제하여 보안성 및 저장 공간 효율성 증대.
- [x] **삭제 이력 요약(Cleanup Summary)**: 삭제된 데이터의 파일명, 처리 시각, 처리 건수를 기록한 별도의 리포트 파일을 생성하여 추후 정합성 검증 및 이력 관리 용도로 활용.

---

## 9. [차세대] AWS Lambda & 데이터 레이크 아키텍처 (Next-Gen Architecture)

기존 파이프라인을 AWS Lambda 및 클라우드 네이티브 환경에 최적화하고, 데이터 관리의 투명성을 높이기 위한 고도화 설계입니다.

### [구현 상태 요약]
| 기능 구분 | 주요 내용 | 상태 | 비고 |
| :--- | :--- | :---: | :--- |
| **데이터 저장** | crawling (TC10) 테이블 전환 | `[x]` | 03_preprocess_... 반영 완료 |
| **데이터 레이크** | Hive Style 계층적 폴더 구조 | `[x]` | get_hive_path() 구현 완료 |
| **품질 표준** | 한국어 주석 및 클린 코드 | `[x]` | 전 모듈 적용 완료 |
| **환경 격리** | `raw/clean/save` 및 `requirements.txt` | `[x]` | 단계별 폴더 및 독립 환경 구축 완료 |
| **품질 표준** | Any/Unknown 타입 금지 (엄격한 타입) | `[x]` | 전 모듈 Type Hinting 완료 |
| **품질 표준** | `print()` 제거 및 `logging` 도입 | `[x]` | 전 모듈 적용 완료 |

### 9-1. 데이터 저장 전략 변경 (Review Storage Pivot)
- [x] **리뷰 데이터 적재 대상 변경**: 기존 `posts` 테이블에 직접 저장하던 방식을 중단하고, 모든 수집 데이터는 일차적으로 `crawling` (TC10) 테이블에 저장합니다.
- [ ] **검증 파이프라인 도입**: `crawling` 테이블에 저장된 데이터를 기반으로 자동 생성 파이프라인(Validation Pipeline)을 실행하여 정합성이 검증된 데이터만 최종 서비스 테이블로 이동시킵니다.

### 9-2. 하이브 스타일 데이터 레이크 구조 (Hive-style Partitioning)
- [x] **계층 구조 도입**: 데이터의 생명주기를 명확히 관리하고 쿼리 효율성을 높이기 위해 `item=value` 형식의 계층적 디렉� - 최종 저장한 데이터들은 계층화가 아예 안됨
 - 리뷰 크롤링 자체는 진행이 안됨
 - 리뷰 데이터를 수집해서 그 데이터가 크롤링 테이블에 들어가고 맛집 디테일 데이터(메뉴, 가격등)가 maps, shop, menu, image 테이블로 안들어감
 - kakao api를 이용한 위경도를 가져오는 프로그램도 구현이 안됨

---

## 14. [검토 및 차기 수정 계획] 2026-04-15 (Revision & Action Plan)

사용자의 지적 사항과 현재 코드베이스를 전수 대조한 결과, **표면적인 구조는 잡혀 있으나 실질적인 데이터 흐름에서 누락된 핵심 기능**들이 확인되었습니다. 이를 해결하기 위한 구체적인 수정 계획입니다.

### 14-1. 미비점 상세 분석 결과

1.  **이미지 데이터 방치 (`images` 테이블 누락)**
    - 현상: `meal_detail/save/upload_shop_to_db.py`에 이미지 적재 로직이 없음.
    - 원인: 상세 수집(`collect_details.py`) 단계에서 이미지 URL을 충분히 수집하지 않거나, 적재기에서 이를 무시함.
2.  **리뷰 파이프라인 작동 불능**
    - 현상: 리뷰 수집 스크립트가 존재하나 실제 데이터가 `crawling` 테이블에 유의미하게 쌓이지 않음.
    - 원인: 다이닝코드의 동적 로딩(무한 스크롤)과 리뷰 탭 클릭 이벤트 처리가 미흡하여 빈 CSV만 생성됨.
3.  **데이터 계층화 관리 부족**
    - 현상: 데이터 레이크(Hive) 경로는 생성되지만, DB 테이블상에서 특정 수집 회차(Batch)를 구분할 수 있는 식별자가 없음.
    - 원인: `maps`, `shop` 테이블 설계 시 수집 시점이나 소스 버전을 기록하는 컬럼이 활발히 활용되지 않음.
4.  **카카오 API 연동 실효성**
    - 현상: 위경도 값이 `0.0`으로 들어가는 경우가 많음.
    - 원인: API 키 전달 방식은 구현되었으나, 주소 정규화(Normalization) 부족으로 카카오 맵 검색 실패율이 높음.

### 14-2. 향후 수정 계획 (Action Items)

| 순번 | 작업 항목 | 목표 및 기대 효과 | 대상 파일 |
| :---: | :--- | :--- | :--- |
| **1** | **이미지 적재 로직 추가** | 상세 수집 시 이미지 URL 포함 및 `images` 테이블 insert (FK 연결) | `collect_details.py`, `upload_shop_to_db.py` |
| **2** | **리뷰 수집 로직 보정** | 무한 스크롤 및 '리뷰 더보기' 클릭 강화로 실제 리뷰 텍스트 수집 보장 | `collect_reviews.py` |
| **3** | **배치 관리 컬럼 강화** | `crawling` 테이블뿐만 아니라 `shop` 등에도 `batch_id`(수집일시)를 기록하여 계층 관리 | `members.py`, 각 적재 스크립트 |
| **4** | **주소 정규화 고도화** | 주소에서 불필요한 수식어 제거 후 Kakao API 호출하여 위경도 적중률 향상 | `common_utils.py`, `upload_shop_to_db.py` |
| **5** | **통합 테스트 실행** | `run_batch_pipeline.py`를 `targets_test.csv`로 돌려 `images`까지 들어가는지 최종 검증 | `run_batch_pipeline.py` |

### 14-3. 진행 방식 (Workflow)
1. **[Step 1]** `common_utils.py`에 주소 정규화 및 이미지 처리 헬퍼 함수 보강.
2. **[Step 2]** `meal_detail/raw/collect_details.py`에서 식당 대표/메뉴 이미지 URL 수집 로직 추가.
3. **[Step 3]** `meal_detail/save/upload_shop_to_db.py`에서 `images` 테이블 연동 코드 삽입.
4. **[Step 4]** 리뷰 수집기의 Selector를 최신 다이닝코드 구조에 맞춰 전면 수정.
5. **[Step 5]** 전체 파이프라인 재실행 및 DB 정합성 최종 확인.

---
**업데이트 완료**: 2026-04-15. 프로젝트의 결함을 인정하고 이를 해결하기 위한 기술적 로드맵을 수립하였습니다. 곧바로 [Step 1]부터 수정을 진행할 수 있는 상태입니다. 
awling/maps/shop/menu/images 정의 |
| .gitignore | `.gitignore` | Hive 경로 패턴으로 업데이트 완료 |

---

### 미구현 / 문제 항목

#### [문제 1] upload_reviews_to_db.py — bigint 버그 동일 존재
- `upload_to_db.py`에서 발생한 `bigint out of range` 버그와 **동일한 `int(r["view_count"])` raw 변환 코드**가 존재
- 리뷰 DB 적재 시 동일한 오류 발생 예정
- **수정 필요**: `_safe_int()`, `_safe_float()`, `_safe_bigint()` 안전 변환 함수 적용

#### [문제 2] maps / shop / menu / images 테이블 미적재
- `meal_detail/raw/collect_details.py`가 메뉴, 주소, 평점 등을 수집하지만
- `meal_detail/save/upload_to_db.py`는 **전부 crawling 테이블에만 적재**
- `maps`, `shop`, `menu`, `images` 테이블로 분기하는 적재 로직이 **전혀 없음**
- **신규 구현 필요**: 상세 데이터 → maps/shop/menu/images 적재 스크립트

#### [문제 3] Kakao API 위경도 연동 미완성
- `common_utils.py`에 `fetch_coordinates_kakao()` 함수가 정의되어 있으나
- 어느 스크립트에서도 **실제로 호출되지 않음**
- `maps` 테이블의 `latitude`, `longitude` 컬럼에 값을 채우는 경로가 없음
- **신규 구현 필요**: 주소 → Kakao API → (latitude, longitude) 연동

#### [문제 4] 리뷰 파이프라인 실제 미검증
- `collect_reviews.py`, `preprocess_reviews.py`, `upload_reviews_to_db.py` 코드는 존재하나
- 실제로 끝까지 성공한 이력 없음 (DB 연결 오류로 중단)
- preprocess_reviews.py 출력 컬럼과 upload_reviews_to_db.py 입력 컬럼 정합성 검증 필요

---

### 향후 작업 우선순위

| 순위 | 작업 | 대상 파일 |
| :---: | :--- | :--- |
| 1 | upload_reviews_to_db.py bigint 버그 수정 | `meal_review/save/upload_reviews_to_db.py` |
| 2 | maps / shop / menu / images 테이블 적재 스크립트 신규 구현 | `meal_detail/save/` 하위 신규 파일 |
| 3 | Kakao API 위경도 연동 — fetch_coordinates_kakao 실제 호출 연결 | `meal_detail/save/` 내 maps 적재 로직 |
| 4 | 리뷰 파이프라인 전체 실행 검증 | `meal_review/` 전 단계 |

---

## 13. [구현 완료] 2026-04-15 코드 구현 결과

### 변경/신규 파일 목록

| 구분 | 파일 | 변경 내용 |
| :---: | :--- | :--- |
| 수정 | `meal_review/save/upload_reviews_to_db.py` | bigint 버그 수정, 안전 변환 함수 적용 |
| **신규** | `meal_detail/save/upload_shop_to_db.py` | maps / shop / menu 테이블 적재 스크립트 |
| 수정 | `run_batch_pipeline.py` | Detail-Save-Shop 단계 추가, kakao-api-key 인자 추가 |
| 수정 | `meal_review/clean/preprocess_reviews.py` | category_cd None → CA01 기본값 수정 |

---

### 최종 파이프라인 실행 흐름

```
[Stage 1] 맛집 상세 정보
──────────────────────────────────────────────────────────────────
 1-1. Detail-Raw-Links
      collect_links.py
      → process=raw/service=shop/.csv (URL 목록)

 1-2. Detail-Raw-Details
      collect_details.py --input <raw/shop CSV>
      → process=raw/service=shop/.csv (메뉴·주소·평점 포함)

 1-3. Detail-Save-Shop  ← [신규 추가]
      upload_shop_to_db.py --input <raw/shop CSV>
      → maps 테이블  (store_name, Kakao API 위경도, address_cd)
      → shop  테이블 (map_id FK, food_category_cd, rating)
      → menu  테이블 (shop_id FK, menu_name, price)

 1-4. Detail-Clean-Preprocess
      preprocess.py --input <raw/shop CSV>
      → process=cleansing/service=shop/.csv (crawling 포맷)

 1-5. Detail-Save-DB
      upload_to_db.py --input <cleansing/shop CSV>
      → crawling 테이블 (thread='shop', 게시글 형태로 보존)

[Stage 2] 리뷰 데이터
──────────────────────────────────────────────────────────────────
 2-1. Review-Raw-Collection
      collect_reviews.py --input <raw/shop CSV>
      → process=raw/service=review/.csv (리뷰 원본)

 2-2. Review-Clean-Preprocess
      preprocess_reviews.py --input <raw/review CSV>
      → process=cleansing/service=review/.csv (crawling 포맷)

 2-3. Review-Save-DB
      upload_reviews_to_db.py --input <cleansing/review CSV>
      → crawling 테이블 (thread='review', 리뷰 원문 보존)
```

### 데이터 흐름 요약

```
수집(Playwright) → Hive CSV 저장 → DB 적재
                                     ├─ maps  / shop / menu  (구조화된 맛집 정보)
                                     └─ crawling              (원본 보존 스테이징)
```

### 주요 설계 결정 사항

- **Kakao API 위경도**: `common_utils.fetch_coordinates_kakao()` 가 정의만 되어있고 호출되지 않았던 문제를 `upload_shop_to_db.py` 에서 실제 호출하여 해결. API 키 미설정 시 `0.0` 으로 fallback 처리하여 파이프라인이 중단되지 않도록 설계.
- **중복 방지**: maps `(name + address_detail)`, shop `(map_id)`, menu `(shop_id + name)` 세 단계 모두 `SELECT → 존재 시 스킵` 패턴으로 멱등성 확보.
- **bigint 버그**: psycopg2 가 Python `int` 를 PostgreSQL `bigint` 로 전송할 때 DB 컬럼 타입이 `INT` 이면 범위 초과 오류가 발생. `_safe_int()` / `_safe_float()` / `_safe_bigint()` 헬퍼로 해결.
- **category_cd None 문제**: `preprocess_reviews.py` 에서 `None` 을 저장하면 CSV 로드 후 문자열 `"None"` 으로 읽혀 codeT FK 위반이 발생. `CA01` 기본값으로 수정.

### 중요 참고 사항
- 일단은 crawling 테이블은 meal_review 폴더에서 수집한 부분만 적재할거야
- 나머지 meal menu, images, shop, maps 테이블에다가 meal_detail 폴더에서 수집한 부분만 적재할거야