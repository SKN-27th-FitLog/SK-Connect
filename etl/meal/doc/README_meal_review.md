# 식당 리뷰 파이프라인 (meal_review) 추가 및 경로 오류 수정

가게 상세 정보를 수집하는 기존 `meal_detail` 파이프라인과 완벽히 호환되도록 리뷰 파이프라인 단계를 구축완료했습니다.

## 1. 전역 Data 폴더 경로 일괄 수정
현재 스크린샷 구조에서 보듯 `data/` 폴더가 프로젝트 최상단 디렉토리(`food crawlring/data/`)로 노출되어 있었습니다.
이 때문에 `meal_detail` 내부에 있는 코드들이 실행될 때, 잘못된 위치에 파일을 생성하거나 찾지 못하는 오류를 방지하기 위해 다음 스크립트 내부의 **모든 기본 경로(default path)들을 `../data/...` 형태로 수정**했습니다.
- [MODIFY] `meal_detail/01_collect_store_links.py`
- [MODIFY] `meal_detail/02_collect_store_details.py`
- [MODIFY] `meal_detail/03_preprocess_and_upload.py`

---

## 2. 리뷰 파이프라인 신규 구축 (`meal_review`)

의견 주신대로 리뷰 또한 "상세수집(02)" -> "업로드(03)" 구조로 단계를 명확히 나누고, 가게별로 JSON 파일을 생성하도록 코드를 만들었습니다.

### [NEW] `meal_review/02_collect_store_reviews.py`
- 검색 기능을 버리고, `meal_detail` 시스템이 저장한 `../data/raw_store_data.csv`의 **`store_url` 목록으로 직접 순회**하도록 수정해 속도와 정확도를 대폭 끌어올렸습니다.
- **이미지 다운로드 기능**: 리뷰 본문에 포함된 **음식 사진(`<img>` 속성)** 들을 감지하여 고화질 원본 해상도로 자동 추출합니다. 더보기를 클릭하지 않아도 화면에 즉시 로딩되는 음식/장소 사진들만 쏙쏙 뽑아냅니다.
- **아웃풋 분리**: 모든 리뷰 결과물은 기존 `data` 폴더와 충돌하지 않도록 독립된 **`../review_data/`** 에 저장됩니다.
  - JSON 텍스트 파싱 결과: `../review_data/jsons/{번호}_{가게명}.json`
  - 이미지 물리적 저장: `../review_data/images/{가게명}/...` 

### [MODIFY] `meal_review/03_preprocess_and_upload_reviews.py`
- `../review_data/jsons/*.json` 을 모두 읽어들여 단일 DataFrame으로 생성하며, `review.csv` 백업을 `../review_data/` 에 만듭니다.
- **[핵심]** 파싱한 리뷰를 `posts` 및 `images` 통합 테이블 시스템으로 삽입합니다. (크롤러 봇 전용 계정 `crawler_bot` 자동 매핑) 내용에는 파싱된 평점과 키워드를 합칩니다 (`[평점: X.X] \n 본문...`).
- **자동 정리(Auto Cleanup)**: DB 업로드가 안전하게 커밋 완료되면, 로컬에 생성된 JSON 및 CSV 임시 파일들을 모두 영구적으로 삭제하여 저장 공간을 절약하고 민감 정보를 남기지 않습니다.

> [!TIP]
> 상세 수집과 리뷰 수집 과정을 번거롭게 일일이 칠 필요 없이 상위 폴더(`etl/meal/run_batch_pipeline.py`)에서 원 클릭 배치 스크립트로 동작시키는 것이 규칙입니다!
> ```bash
> # etl/meal 폴더에서 실행
> python run_batch_pipeline.py --targets meal_detail/targets_example.csv --host ... --dbname ... --user ... --password ...
> ```
