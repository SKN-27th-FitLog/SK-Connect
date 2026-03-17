# 지도 구현 작업 플랜

- 진행 요약·수정 이력은 이 문서를 보면서 기록하며 진행합니다.
- 구현은 가이드(주석·코드 블록 설명)를 참고해 직접 작성하고, 완료 후 평가 요청 시 이 문서의 평가 기준으로 점검합니다.

---

## 1. 진행 요약

| 항목 | 내용 |
|------|------|
| 현재 단계 | (진행 시 채움) |
| 완료한 항목 | (예: 요구사항 4 config 확장) |
| 다음 할 일 | (예: 요구사항 6 우측 컨트롤) |

---

## 2. 진행 및 수정 이력

| 날짜 | 수정 파일 | 수정 내용 | 비고 |
|------|-----------|-----------|------|
|  |  |  |  |

---

## 3. 참고 자료

- **react-kakao-maps-sdk 샘플**: https://react-kakao-maps-sdk.jaeseokim.dev/docs/sample  
  - 지도 레벨/이동, 컨트롤, 확대·축소 이벤트, 마커, geolocation
- **Kakao 지도 웹 샘플**: https://apis.map.kakao.com/web/sample/
- **프로젝트 지도 API**: [api_doc.md](api_doc.md) §6 주변 위치 게시글 마크 업데이트 / 게시글 마크 정보 요청

---

## 4. 요구사항별 가이드

### 요구사항 1 · 네비게이터 통해 지도 화면 진입 시 표시

- **적용 파일**: RootNavigator (타 팀 작업 분이므로 수정하지 않음)
- **확인 사항**: Map 탭 선택 시 MapScreen이 노출되는지만 확인.

---

### 요구사항 2 · 지도 화면 구현 (지도 API로 초기 표시)

- **적용 파일**: `front/src/screens/MapScreen.web.js`, `front/src/screens/MapScreen.js`
- **가이드**: 웹은 카카오맵 `Map`으로 초기 표시, 네이티브는 placeholder 유지. 초기 중심·줌은 config 사용.

---

### 요구사항 3 · 표시 위치 = 기기 현재 위치

- **적용 파일**: 추후 구현. 현재는 (4) config 값 사용.
- **가이드**: 실제 구현 전까지는 생략. 준비만 주석으로 명시.

---

### 요구사항 4 · 현재 위치는 config 값으로 사용

- **적용 파일**: `front/src/config/map.js`
- **가이드**: `DEFAULT_LOCATION` 유지. 초기 지도 중심·현재 위치 대체용으로 사용한다고 주석 명시.

---

### 요구사항 5 · 지도 Pin은 config로 준비

- **적용 파일**: `front/src/config/map.js`
- **가이드**: `MAP_PINS`를 지도 pin 소스로 사용. 추가 pin이 필요하면 여기에 항목 추가.

---

### 요구사항 6 · 지도 우측: 내 현재위치로 이동, 확대, 축소

- **적용 파일**: `front/src/screens/MapScreen.web.js`
- **가이드**: `react-kakao-maps-sdk`의 `ZoomControl` position `RIGHT`. "내 위치로 이동" 버튼은 Map ref로 `setCenter(DEFAULT_LOCATION)` 호출. 우측에 세로로 배치.

---

### 요구사항 7 · 확대·축소 정도 지정 가능

- **적용 파일**: `front/src/config/map.js`, `front/src/screens/MapScreen.web.js`
- **가이드**: config에 `DEFAULT_ZOOM_LEVEL`, `ZOOM_LEVEL_MIN`, `ZOOM_LEVEL_MAX` 추가. Map의 `level` props 및 확대/축소 버튼에서 해당 값 사용·클램프.

---

### 요구사항 8 · 초기 화면 기본 확대 배율 지정

- **적용 파일**: `front/src/config/map.js`, `front/src/screens/MapScreen.web.js`
- **가이드**: Map 초기 `level={DEFAULT_ZOOM_LEVEL}`. config에 `DEFAULT_ZOOM_LEVEL` 정의.

---

### 요구사항 9 · 화면 드래그 시 지도 이동

- **적용 파일**: `front/src/screens/MapScreen.web.js`
- **가이드**: SDK 기본 동작. 드래그 막지 않으면 됨. 필요 시 `draggable` 옵션 확인.

---

### 요구사항 10 · Pin 중간 다리 (중심 좌표·개수 로딩 대비, 당장 구현 X)

- **적용 파일**: `front/src/api/mapApi.js`
- **가이드**: `getMapMarkers(center?)` 시그니처 유지. 지도는 "pin 배열을 전달받아 표시"만 하며, 추후 이 함수 내부에서 중심 좌표·개수로 API 호출하도록 확장. 해당 의도 주석으로 명시.

---

## 5. 평가 기준

- **동작**: 지도 진입 시 초기 표시, config 중심/줌, 우측 확대·축소·현재위치, 드래그 이동, pin 표시·클릭 시 팝업이 기대대로 동작하는지.
- **작성**: config·mapApi·화면 역할 분리, 주석과 플랜 문서 참조가 일치하는지.

---

*이 문서는 지도 구현 진행 시 업데이트하며 사용합니다.*
