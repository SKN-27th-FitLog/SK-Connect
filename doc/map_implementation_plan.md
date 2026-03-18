# 지도 구현 작업 플랜

- 진행 요약·수정 이력은 이 문서를 보면서 기록하며 진행합니다.
- 구현은 가이드(주석·코드 블록 설명)를 참고해 직접 작성하고, 완료 후 평가 요청 시 이 문서의 평가 기준으로 점검합니다.

---

## 1. 진행 요약

| 항목 | 내용 |
|------|------|
| 현재 단계 | 지도는 **WebView + 카카오 JS SDK** (`KakaoMapWebView`). `@jiggag` 네이티브 카카오맵 **미사용·제거**. 화면 진입: `screens/MapScreen.js`. |
| 완료한 항목 | 요구사항 2·4·5·10, 스타일·MapPostPreviewCard, `react-native-webview`, `EXPO_PUBLIC_KAKAO_MAP_JS_KEY` 기반 지도 |
| 다음 할 일 | 요구사항 3(기본 중심을 실제 현재 위치로 고정 여부), 기타 UX 다듬기 |
| 검토 필요 | 웹 의존성(react-native-web 등) 버전·실행환경 고정, 지도 로드 실패 시 에러 화면 기획 |

---

## 2. 진행 및 수정 이력

| 날짜 | 수정 파일 | 수정 내용 | 비고 |
|------|-----------|-----------|------|
| 2026-03-16 | doc/map_implementation_plan.md | 초기 플랜 문서 작성, 주석 추가 | |
| 2026-03-16 | front/src/config/map.js | DEFAULT_LOCATION, MAP_PINS, 줌 상수 TODO | |
| 2026-03-16 | front/src/screens/MapScreen.js | MapView + Marker 연동, MapPlaceholder props 수정 | react-native-maps 사용 |
| 2026-03-16 | front/src/styles/map.js | MapScreen·MapPostPreviewCard·MapPinPopup 스타일 통합 | |
| 2026-03-16 | front/src/components/map/MapPostPreviewCard.js | map.js 스타일 사용, location_name 지원 | |
| 2026-03-16 | front/src/components/map/MapPinPopup.js | map.js 스타일 사용, content/description 지원 | |
| 2026-03-16 | front/package.json | react-native-maps 제거, @jiggag/react-native-kakao-maps 추가 | 카카오맵 |
| 2026-03-16 | front/src/screens/MapScreen.js | KakaoMapView 적용, 마커 클릭 미지원 → 하단 주변 게시글 목록으로 선택 | |
| 2026-03-16 | front/src/styles/map.js | pinListScroll, pinListItem 등 주변 게시글 목록 스타일 추가 | |
| 2026-03-16 | front/package.json | react-kakao-maps-sdk 추가 | 웹 지도 |
| 2026-03-16 | front/src/screens/MapScreen.web.js | MapPostPreviewCard·map.js 스타일 사용, 인라인 popup 제거 | npm run web으로 확인 |
| 2026-03-17 | front/src/navigation/RootNavigator.js | Platform.OS로 MapScreen (web/native) 분기 | 웹에서 첫 페이지 미표시 해결. 요구사항 1 부득이 수정 |
| 2026-03-17 | front/package.json | react-native-web, @expo/metro-runtime 추가 | 웹 실행 필수. 다중 브랜치 버전·실행환경 고정 이슈 검토 필요 |
| 2026-03-17 | front/src/screens/MapScreen.web.js | 지도 로드 실패 시 도메인 등록 안내 메시지 추가 | 확정 여부 미결정. 에러 화면 별도 기획 검토 필요 |
| 2026-03-18 | front | @jiggag/react-native-kakao-maps **코드·의존성 제거**. `KakaoMapWebView` + `screens/MapScreen.js`로 전환 | Expo Go에서 지도 확인 가능 |
| 2026-03-18 | front | `MAP_DEFAULT_LEVEL`·MIN/MAX, `MapMapControls`(줌·내위치), `expo-location`, `KakaoMapWebView` ref inject, `.env.example`, app.json location 플러그인 | 플랜 요구사항 6·7·8 반영 |

---

## 3. 스타일 및 컴포넌트 정리

### 3.1 스타일 통합 (`front/src/styles/map.js`)

지도 관련 스타일은 **이 파일 한 곳**에서만 정의하고, 하위 컴포넌트는 모두 여기서 import 해 사용합니다.

| 구분 | 스타일 키 | 용도 |
|------|-----------|------|
| **MapScreen** | container, mapArea, mapPlaceholderText, mapWebViewContainer, mapWebView, mapWebViewFallback | 지도 화면·WebView 영역 |
| **팝업 공통** | popupOverlay, popup, popupHeader, popupCategory, popupClose, popupTitle, popupContent, popupLocation, popupButton, popupButtonText | 팝업 레이아웃·텍스트 |
| **MapPostPreviewCard** | postPreviewCard, postPreviewHeaderRow, postPreviewCategory, postPreviewClose, postPreviewTitle, postPreviewContent, postPreviewLocation, postPreviewButton, postPreviewButtonText | 게시글 미리보기 카드 |
| **MapPinPopup** | pinPopupContainer, pinPopupTitle, pinPopupDescription, pinPopupButtonRow, pinPopupButtonPrimary, pinPopupButtonSecondary, pinPopupButtonText | 단순 핀 팝업 |

### 3.2 컴포넌트 역할

| 파일 | 역할 | 스타일 소스 |
|------|------|-------------|
| `front/src/screens/MapScreen.js` | UX 정의(상태, 핸들러, 표시 조건) | map.js |
| `front/src/components/map/KakaoMapWebView.js` | WebView + JS SDK, ref(setCenter/zoom), 마커 클릭 postMessage | map.js |
| `front/src/components/map/MapMapControls.js` | 우측 확대·축소·내 위치 버튼 | map.js |
| `front/src/components/map/MapPostPreviewCard.js` | 게시글 미리보기 카드 | map.js |
| `front/src/components/map/MapPinPopup.js` | 단순 핀 정보 팝업 | map.js |

### 3.3 데이터 흐름

- **pin 구조**: `{ id, postId, lat, lng, title, content, category, location_name }`
- **MapPostPreviewCard**: `post.location` 또는 `post.location_name` 지원
- **MapPinPopup**: `pin.description` 또는 `pin.content` 지원

---

## 4. 실행 파일 및 구조

### 4.1 앱 진입 경로

```
index.js
  └── App.js (NavigationContainer, SafeAreaProvider)
        └── AppNavigator (Stack)
              └── MainTabs (RootNavigator, Tab)
                    ├── Home (PostListScreen)
                    ├── Community (CommunityScreen)
                    ├── Chat (ChatScreen)
                    ├── Map (MapScreen)  ← 지도 화면
                    └── MyPage (MyPageScreen)
```

### 4.2 지도 화면 구조 (`MapScreen.js`)

```
MapScreen
  ├── mapScreenStyles (front/src/styles/map.js)
  ├── KakaoMapWebView (center, pins, onMarkerPress)
  ├── ScrollView (주변 게시글 목록)
  └── MapPostPreviewCard (선택된 핀 팝업)
```

### 4.3 의존 파일 목록

| 경로 | 역할 |
|------|------|
| `front/src/navigation/RootNavigator.js` | Map 탭: MapScreen 로드 (앱 기준) |
| `front/src/screens/MapScreen.js` | 지도 화면 (KakaoMapWebView) |
| `front/src/screens/MapScreen.web.js` | 더 이상 사용하지 않음 (웹 실행 미지원 상태) |
| `front/src/styles/map.js` | 지도 관련 스타일 통합 |
| `front/src/components/map/MapPostPreviewCard.js` | 게시글 미리보기 팝업 |
| `front/src/components/map/MapPinPopup.js` | 단순 핀 팝업 (선택 시 사용) |
| `front/src/config/map.js` | DEFAULT_LOCATION, MAP_PINS |
| `front/src/api/mapApi.js` | getMapMarkers (pin 중간 다리) |

### 4.4 실행 방법

**웹 (npm run web)** – 지도 확인에 가장 간단합니다.

```bash
cd front
npm install
npm run web
```

- `.env`에 `EXPO_PUBLIC_KAKAO_MAPS_JAVASCRIPT_KEY` 설정 필요
- [카카오 개발자 콘솔](https://developers.kakao.com/) → 플랫폼 → Web에서 `http://localhost:8081` 등 허용 도메인 등록

---

**앱 (Expo Go / 에뮬레이터)**: `.env`에 **JavaScript 키**를 넣는다.

- `EXPO_PUBLIC_KAKAO_MAP_JS_KEY` — [카카오 개발자 콘솔](https://developers.kakao.com/) 앱 키 중 **JavaScript 키**와 동일 값.

```bash
cd front
npm install   # 또는 yarn
npx expo start
```

지도는 WebView에서 JS SDK를 로드하므로 **별도 네이티브 카카오맵 SDK(@jiggag 등)는 사용하지 않는다.**

---

## 5. 참고 자료

- **react-kakao-maps-sdk 샘플**: https://react-kakao-maps-sdk.jaeseokim.dev/docs/sample  
  - 지도 레벨/이동, 컨트롤, 확대·축소 이벤트, 마커, geolocation
- **Kakao 지도 웹 샘플**: https://apis.map.kakao.com/web/sample/
- **프로젝트 지도 API**: [api_doc.md](api_doc.md) §6 주변 위치 게시글 마크 업데이트 / 게시글 마크 정보 요청

---

## 6. 요구사항별 가이드

### 요구사항 1 · 네비게이터 통해 지도 화면 진입 시 표시

- **적용 파일**: `front/src/navigation/RootNavigator.js`
- **상태**: Map 탭 선택 시 MapScreen 노출됨.
- **비고**: 웹이 아닌 환경에서는 지도 동작 확인이 어려워, 웹 실행 시 첫 페이지가 표시되도록 Platform.OS로 MapScreen/MapScreen.web 분기 적용. (원래는 타 팀 담당으로 수정 예정이 아니었으나 부득이하게 수정)

---

### 요구사항 2 · 지도 화면 구현 (지도 API로 초기 표시)

- **적용 파일**: `front/src/screens/MapScreen.js`
- **상태**: KakaoMapWebView, DEFAULT_LOCATION 기준 중심·핀 표시. 마커 클릭·하단 목록 모두 선택 가능.

---

### 요구사항 3 · 표시 위치 = 기기 현재 위치

- **적용 파일**: 추후 구현. 현재는 (4) config 값 사용.
- **가이드**: 실제 구현 전까지는 생략. 준비만 주석으로 명시.

---

### 요구사항 4 · 현재 위치는 config 값으로 사용

- **적용 파일**: `front/src/config/map.js`
- **상태**: DEFAULT_LOCATION 사용 중. 초기 지도 중심에 적용됨.

---

### 요구사항 5 · 지도 Pin은 config로 준비

- **적용 파일**: `front/src/config/map.js`
- **상태**: MAP_PINS 사용. mapApi.getMapMarkers에서 반환.

---

### 요구사항 6 · 지도 우측: 내 현재위치로 이동, 확대, 축소

- **적용 파일**: `front/src/screens/MapScreen.js`, `MapMapControls.js`, `KakaoMapWebView.js`
- **상태**: `MapMapControls` + `expo-location`으로 내 위치, `KakaoMapWebView` ref로 줌 인/아웃.

---

### 요구사항 7 · 확대·축소 정도 지정 가능

- **적용 파일**: `front/src/config/map.js` (`MAP_LEVEL_MIN`, `MAP_LEVEL_MAX`, `MAP_DEFAULT_LEVEL`)
- **상태**: Kakao맵 level 범위로 줌 한 단계씩 제한.

---

### 요구사항 8 · 초기 화면 기본 확대 배율 지정

- **적용 파일**: `front/src/config/map.js` (`MAP_DEFAULT_LEVEL`), `MapScreen.js` → `KakaoMapWebView`에 전달.

---

### 요구사항 9 · 화면 드래그 시 지도 이동

- **적용 파일**: `front/src/screens/MapScreen.js`
- **상태**: react-native-maps 기본 동작으로 드래그 이동 가능.

---

### 요구사항 10 · Pin 중간 다리 (중심 좌표·개수 로딩 대비)

- **적용 파일**: `front/src/api/mapApi.js`
- **상태**: getMapMarkers(center?) 시그니처 유지. 현재 config 고정 반환. 추후 내부만 API 연동.

---

## 7. 미확정·검토 필요 항목 (현재 작업 범위: 앱 실행 기준)

### 7.1 웹 의존성 (react-native-web, @expo/metro-runtime)

- **상태**: 현재 작업 범위에서는 웹 실행을 고려하지 않음. 필요 시 별도 검토.
- **이슈**: 여러 브랜치에서 웹 실행을 병행할 경우 버전·실행환경 고정 문제가 발생할 수 있음.
- **후속**: 웹 지원을 재개할 때 버전 관리 전략, 브랜치별 실행환경 일관성 검토.

### 7.2 지도 로드 실패 시 표시 화면 (웹)

- **상태**: 웹 실행을 현재 고려하지 않아, 우선순위에서 제외.
- **고려사항**: 웹 지원을 재개한다면, 지도 로드 실패 시나리오(도메인 등록, API 키 문제 등)에 대한 에러 화면을 별도 기획·설계할 필요가 있음.
- **후속**: 웹 지원 재개 시점에 UX 기획 후 구현 여부 결정.
---

## 8. 평가 기준

- **동작**: 지도 진입 시 초기 표시, config 중심/줌, pin 표시·클릭 시 팝업, 드래그 이동이 기대대로 동작하는지.
- **작성**: config·mapApi·화면 역할 분리, 스타일은 map.js에서만 정의, 주석과 플랜 문서 참조가 일치하는지.

---

## 9. 지도 기능 관련 의존성 정리 (FE 버전 관리 참고용)

- **`react-native-webview`** (필수)  
  - 역할: 카카오맵 JS SDK를 로드하는 WebView. `KakaoMapWebView.js`에서 사용.  
  - 설치: `npx expo install react-native-webview` (Expo SDK와 맞는 버전).

- **`@jiggag/react-native-kakao-maps`**  
  - **사용하지 않음. package.json·코드에서 제거됨.**

- **`react-kakao-maps-sdk`**  
  - 현재 지도 구현과 무관(과거 웹 전용 시도). 사용 시에만 추가.

- **환경 변수: `EXPO_PUBLIC_KAKAO_MAP_JS_KEY`**  
  - 카카오 콘솔 **JavaScript 키**와 동일. 지도 SDK `appkey`로 사용.

- **`expo-location`**  
  - 내 위치 버튼(`MapMapControls`). `app.json`에 플러그인 권한 문구 설정.
- **`.env.example`**  
  - `EXPO_PUBLIC_KAKAO_MAP_JS_KEY` 안내.

---

*이 문서는 지도 구현 진행 시 업데이트하며 사용합니다.*
