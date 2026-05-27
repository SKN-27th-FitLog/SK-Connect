# DiningCode 음식 이미지 수집 설계

## 배경

현재 DiningCode 이미지 수집은 `photo_section`의 사진 탭을 순회하며 `food`, `interior`, `exterior`, `menu_info` 카테고리의 이미지를 모두 `photo_data`로 수집할 수 있다. 사용 목적은 식당의 대표 음식 이미지를 확보하는 것이므로, 실내, 실외, 메뉴 정보, 리뷰 내부 이미지는 `images` 적재 대상에서 제외한다.

## 확정 요구사항

- DiningCode 이미지 수집 대상은 `section.photo_section` 안의 음식 탭(`data-sort-value="food"`)으로 제한한다.
- 이미지 URL은 음식 탭의 `#photos_container .photo_box[data-origin]`에서 원본 URL을 가져온다.
- `data-origin`이 없거나 HTTP URL이 아닌 값은 수집하지 않는다.
- `interior`, `exterior`, `menu_info` 탭 이미지는 수집하지 않는다.
- 리뷰 내부에서 추출되는 `review_images`는 `images` 테이블 적재 대상에 포함하지 않는다.
- 이미지 파일 다운로드는 하지 않고, 기존 구조처럼 URL 메타데이터만 수집한다.
- Stage4 저장 방식은 기존 계약을 유지한다. 수집된 음식 이미지는 `<img src="..." alt="식당 이미지"/>` 형식으로 변환되어 `images`에 적재된다.

## 비범위

- Naver, Google, Kakao, Recipe10000 이미지 수집 추가는 포함하지 않는다.
- `images` 테이블 스키마 변경은 포함하지 않는다.
- `TC10/crawling_id` 연결 기준을 `TC08/shop_id`로 변경하지 않는다.
- 기존 seed 데이터의 이미지 태그 형식 정리는 포함하지 않는다.

## 아키텍처

`DiningCodeCollector`는 플랫폼 특화 수집 책임만 가진다. 이미지 카테고리 선택도 DiningCode DOM 구조에 종속된 수집 정책이므로 collector 내부에서 음식 탭만 선택한다.

`DiningCodeParser`는 기존처럼 `photo_data`를 받아 중복 URL을 제거하고 candidate의 `images` 목록으로 변환한다. parser는 `photo_data`에 넘어온 카테고리만 해석하며, 추가 카테고리 필터링 정책을 새로 만들지 않는다.

Stage3와 Stage4는 기존 데이터 흐름을 유지한다. Stage3는 음식 이미지 URL 목록으로 `image_content_hash`를 계산하고, Stage4는 변경이 필요한 경우 기존 `_load_images` 경로로 `images` 테이블에 적재한다.

## 데이터 흐름

1. Stage1이 DiningCode 상세 페이지를 연다.
2. `DiningCodeCollector`가 `section.photo_section`의 음식 탭을 선택한다.
3. 음식 탭이 활성화된 상태에서 `#photos_container .photo_box[data-origin]`를 읽는다.
4. 각 사진을 `{url, category, nickname, date}` 형태로 `photo_data["food"]`에 저장한다.
5. Stage2가 `photo_data["food"]`를 candidate `images`로 변환한다.
6. Stage3가 음식 이미지 목록 기준으로 변경 여부를 판단한다.
7. Stage4가 음식 이미지만 `images` 테이블에 저장한다.

## 오류 처리

- 음식 탭 또는 사진 컨테이너가 없으면 이미지 목록은 빈 리스트로 처리하고, 크롤링 자체를 실패시키지 않는다.
- 탭 클릭 후 DOM 갱신 대기는 짧은 timeout을 사용한다.
- 개별 이미지 항목 파싱 실패는 해당 항목만 건너뛰고 나머지 수집을 계속한다.

## 테스트 기준

- `DiningCodeCollector` 또는 이미지 수집 헬퍼는 음식 탭만 클릭하거나 음식 탭만 대상으로 수집해야 한다.
- `photo_data`에는 `food` 카테고리만 포함되어야 한다.
- `interior`, `exterior`, `menu_info` 이미지는 candidate `images`와 Stage4 적재 입력에 포함되지 않아야 한다.
- 기존 `_load_images`의 `<img>` 태그 변환 및 `TC10/crawling_id` 연결 테스트는 유지되어야 한다.

