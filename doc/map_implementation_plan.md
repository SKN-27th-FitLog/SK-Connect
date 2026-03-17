# 지도 구현 작업 플랜

- 진행 요약·수정 이력은 이 문서를 보면서 기록하며 진행합니다.
- 구현은 가이드(주석·코드 블록 설명)를 참고해 직접 작성하고, 완료 후 평가 요청 시 이 문서의 평가 기준으로 점검합니다.

---

## 1. 진행 요약

| 항목 | 내용 |
|------|------|
| 현재 단계 | react-native-maps → @jiggag 교체 완료. 웹 버전 MapScreen.web.js 정리 완료. 웹 실행을 위한 RootNavigator·의존성 적용. |
| 완료한 항목 | 요구사항 2(지도 화면 구현), 4(config 현재위치), 5(config pin), 10(pin 중간 다리), 스타일 통합, MapPostPreviewCard 연동, 카카오맵 교체(MapScreen.js, package.json), 웹 버전(MapScreen.web.js, react-kakao-maps-sdk), RootNavigator Platform 분기(요구사항 1) |
| 다음 할 일 | 요구사항 6(우측 컨트롤), 7·8(config 줌 레벨), KAKAO_APP_KEY 설정 후 Development Build |
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

---

## 3. 스타일 및 컴포넌트 정리

### 3.1 스타일 통합 (`front/src/styles/map.js`)

지도 관련 스타일은 **이 파일 한 곳**에서만 정의하고, 하위 컴포넌트는 모두 여기서 import 해 사용합니다.

| 구분 | 스타일 키 | 용도 |
|------|-----------|------|
| **MapScreen** | container, mapArea, mapPlaceholderText | 지도 화면 영역 |
| **팝업 공통** | popupOverlay, popup, popupHeader, popupCategory, popupClose, popupTitle, popupContent, popupLocation, popupButton, popupButtonText | 팝업 레이아웃·텍스트 |
| **MapPostPreviewCard** | postPreviewCard, postPreviewHeaderRow, postPreviewCategory, postPreviewClose, postPreviewTitle, postPreviewContent, postPreviewLocation, postPreviewButton, postPreviewButtonText | 게시글 미리보기 카드 |
| **MapPinPopup** | pinPopupContainer, pinPopupTitle, pinPopupDescription, pinPopupButtonRow, pinPopupButtonPrimary, pinPopupButtonSecondary, pinPopupButtonText | 단순 핀 팝업 |

### 3.2 컴포넌트 역할

| 파일 | 역할 | 스타일 소스 |
|------|------|-------------|
| `front/src/screens/MapScreen.js` | UX 정의(상태, 핸들러, 표시 조건) | map.js |
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
  ├── MapPlaceholder (지도 + 마커)
  │     ├── pins (props)
  │     └── KakaoMapView (@jiggag/react-native-kakao-maps)
  │           - markerList, centerPoint, width, height
  ├── ScrollView (주변 게시글 목록 - 마커 클릭 대체 UX)
  │     └── TouchableOpacity[] (pins → 선택 시 MapPostPreviewCard)
  └── MapPostPreviewCard (선택된 핀 팝업)
        ├── post, onClose, onPressViewPost (props)
        └── mapScreenStyles (map.js)
```

### 4.3 의존 파일 목록

| 경로 | 역할 |
|------|------|
| `front/src/navigation/RootNavigator.js` | Map 탭: Platform.OS에 따라 MapScreen(MapScreen.web) 로드 |
| `front/src/screens/MapScreen.js` | 지도 화면 (네이티브) |
| `front/src/screens/MapScreen.web.js` | 지도 화면 (웹, react-kakao-maps-sdk) |
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

**네이티브 (Android/iOS)**: `@jiggag/react-native-kakao-maps`는 네이티브 모듈을 사용하므로 **Expo Go에서 동작하지 않습니다**. Development Build가 필요합니다.

1. **KAKAO_APP_KEY 설정**  
   - [카카오 개발자 콘솔](https://developers.kakao.com/)에서 앱 키 발급  
   - Android: `android/app/src/main/res/values/strings.xml`에 `<string name="kakao_app_key">YOUR_APP_KEY</string>` 추가  
   - iOS: `Info.plist`에 `KAKAO_APP_KEY` 키 추가

2. **빌드 및 실행**

```bash
cd front
npm install
npx expo prebuild   # android/, ios/ 생성 (최초 1회)
npx expo run:android   # 또는 npx expo run:ios
```

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
- **상태**: @jiggag/react-native-kakao-maps KakaoMapView 사용, config(DEFAULT_LOCATION) 기반 초기 표시. 마커 클릭 미지원으로 주변 게시글 목록으로 선택 UX.

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

- **적용 파일**: `front/src/screens/MapScreen.js` (네이티브)
- **가이드**: react-native-maps 기준으로 우측에 버튼 배치. Map ref로 setCamera/setRegion 사용.

---

### 요구사항 7 · 확대·축소 정도 지정 가능

- **적용 파일**: `front/src/config/map.js`, `front/src/screens/MapScreen.js`
- **가이드**: config에 DEFAULT_ZOOM_LEVEL, ZOOM_LEVEL_MIN, ZOOM_LEVEL_MAX 추가. latitudeDelta/longitudeDelta 매핑.

---

### 요구사항 8 · 초기 화면 기본 확대 배율 지정

- **적용 파일**: `front/src/config/map.js`, `front/src/screens/MapScreen.js`
- **상태**: 현재 latitudeDelta/longitudeDelta 0.01 하드코딩. config 상수로 분리 예정.

---

### 요구사항 9 · 화면 드래그 시 지도 이동

- **적용 파일**: `front/src/screens/MapScreen.js`
- **상태**: react-native-maps 기본 동작으로 드래그 이동 가능.

---

### 요구사항 10 · Pin 중간 다리 (중심 좌표·개수 로딩 대비)

- **적용 파일**: `front/src/api/mapApi.js`
- **상태**: getMapMarkers(center?) 시그니처 유지. 현재 config 고정 반환. 추후 내부만 API 연동.

---

## 7. 미확정·검토 필요 항목

### 7.1 웹 의존성 (react-native-web, @expo/metro-runtime)

- **상태**: package.json에 추가됨. 웹 실행에 필요.
- **이슈**: 여러 브랜치에서 실행 시 버전·실행환경 고정 문제가 남아 있음.
- **후속**: 버전 관리 전략, 브랜치별 실행환경 일관성 검토 필요.

### 7.2 지도 로드 실패 시 표시 화면

- **상태**: MapScreen.web.js에 임시 안내(도메인 등록 등) 구현됨. 확정 여부 미결정.
- **고려사항**: 실제 사용자 환경에서 지도 로드 실패 시나리오를 상정한다면, 에러 화면을 별도로 기획·설계하는 작업이 필요함.
- **후속**: 에러 화면 UX 기획 후 구현 확정.

---

## 8. 평가 기준

- **동작**: 지도 진입 시 초기 표시, config 중심/줌, pin 표시·클릭 시 팝업, 드래그 이동이 기대대로 동작하는지.
- **작성**: config·mapApi·화면 역할 분리, 스타일은 map.js에서만 정의, 주석과 플랜 문서 참조가 일치하는지.

---

*이 문서는 지도 구현 진행 시 업데이트하며 사용합니다.*
