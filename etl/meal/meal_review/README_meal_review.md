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

### [NEW] `meal_review/03_preprocess_and_upload_reviews.py`
- `../review_data/jsons/*.json` 을 모두 읽어들여 단일 DataFrame으로 생성하며, `review.csv` 백업을 `../review_data/` 에 만듭니다.
- DB테이블(`review`) 신규 생성 시 **`image_paths`** 컬럼을 추가해 각 리뷰당 저장된 이미지의 로컬 경로 리스트들을 DB에 함께 기록합니다.

> [!TIP]
> 이제 아래의 순서대로 `food crawlring/meal_review/` 폴더에서 실행만 하시면 모든 작업이 완료됩니다!
> ```bash
> # 1. 리뷰 크롤링 실행 (가게별 json 생성)
> python 02_collect_store_reviews.py --headful
> 
> # 2. 수집된 JSON 파일들을 DB로 업로드
> python 03_preprocess_and_upload_reviews.py --host="DB주소" --dbname="디비명" --user="유저명" --password="암호"
> ```
