# SK Connect - 설치 및 실행 가이드

대상 프로젝트의 `front/` 폴더에 SK_Connect 소스를 옮긴 후, 해당 환경에서 설치 및 실행하는 방법입니다.

---

## 0. 타겟 프로젝트 구조 (SK-CONNECT)

대상 브랜치(SK-CONNECT)의 `front/`는 **실행에 필요한 모든 요소를 갖춘 자립형 Expo 앱**입니다. `cd front` 이후 의존성 설치, 실행, 환경 변수 설정 등 모든 작업이 `front/` 폴더 안에서만 이루어집니다. 프로젝트 루트나 backend에 의존하지 않습니다.

**front/ 내부 구조**:

```
front/
├── assets/
├── src/
│   ├── api/
│   ├── components/
│   ├── constants/
│   ├── navigation/
│   └── screens/
├── .gitignore
├── App.js
├── app.json
├── index.js
├── package.json
├── package-lock.json
├── yarn.lock
├── 02023_erd.md
├── README.md
└── 코드 테이블 공부
```

**src 병합 안내**: 타겟 `front/src`에는 api, components, constants, navigation, screens가 있습니다. SK_Connect는 여기에 **config**, **lib**, **theme** 폴더를 추가하고, 공통 폴더는 병합합니다. (INTEGRATION.md 1-1 참고)

**주의사항**:
- `front/App.js`가 있으므로, 예시 코드로 **수정**하거나 기존 구조에 `AppNavigator`를 **통합**합니다.
- `package.json`이 있으므로, 없는 의존성만 추가하고 `npm install`을 `front/` 내부에서 실행합니다.
- `package-lock.json`, `yarn.lock`이 둘 다 있으면 하나만 사용하는 것을 권장합니다. (npm 사용 시 `yarn.lock` 삭제)

---

## 1. 사전 요구사항

- **Node.js** (LTS 권장)
  - [nodejs.org](https://nodejs.org)에서 다운로드
  - 확인: `node -v`, `npm -v`

---

## 2. 의존성 설치

`front/` 폴더로 이동한 뒤, 그 안에서 `npm install`을 실행합니다:

```bash
cd front
npm install
```

> 모든 작업은 `front/` 내부에서 수행됩니다.

### 추가로 필요한 패키지 (없는 경우)

대상 `package.json`에 이미 Expo가 있다면 일부는 포함되어 있을 수 있습니다. 아래 패키지가 없으면 추가하세요:

```bash
npm install @react-navigation/bottom-tabs @react-navigation/native @react-navigation/native-stack
npm install react-native-safe-area-context react-native-screens
npm install react-kakao-maps-sdk
```

**필수 패키지 목록** (참고):

| 패키지 | 용도 |
|--------|------|
| expo | Expo 런타임 |
| react, react-dom, react-native, react-native-web | 핵심 |
| @react-navigation/* | 네비게이션 |
| react-native-safe-area-context, react-native-screens | 네비게이션 의존 |
| react-kakao-maps-sdk | 지도 웹 (MapScreen.web.js) |

---

## 3. 환경 변수 설정

1. `.env.example`을 `.env`로 복사합니다.
2. 카카오 개발자 콘솔에서 **JavaScript 키**를 발급받아 `.env`에 입력합니다.

```
EXPO_PUBLIC_KAKAO_MAPS_JAVASCRIPT_KEY=발급받은_키
```

- **카카오맵 도메인 등록**: 개발자 콘솔에서 `http://localhost`, `http://localhost:8081` 등 사용 도메인을 애플리케이션에 등록해야 합니다.

---

## 4. 최초 실행

`front/` 폴더에서:

```bash
cd front
npm install
npx expo start --web
```

웹 번들 완료 후 브라우저가 자동으로 열립니다. (Metro: http://localhost:8081)

---

## 5. 이후 실행

`front/` 폴더에서:

```bash
cd front
npx expo start --web
```

또는 `npm run web`으로 동일하게 실행할 수 있습니다.

---

## 6. 다른 PC로 옮긴 후

1. **Node.js** 설치
2. **front/** 폴더로 이동 (SK-CONNECT 프로젝트 내 `front` 디렉터리)
3. `front/` 내부에서 `npm install` 실행 (필수, `node_modules`는 복사하지 않음)
4. `front/.env` 생성 및 API 키 설정
5. `front/` 내부에서 `npx expo start --web` 실행

---

## 7. 주요 명령어

| 명령어 | 설명 |
|--------|------|
| `npm install` | 의존성 설치 |
| `npx expo start --web` | 웹 모드로 실행 (권장) |
| `npm run web` | `expo start --web` 단축 |
| `npm run start` | Expo 개발 서버 (w: 웹 전환) |
| `npm run android` | Android 에뮬레이터 |
| `npm run ios` | iOS 시뮬레이터 |

---

## 8. 참고

- **웹 전용**: Expo Go 앱 없이 브라우저에서 실행합니다.
- **의존성**: Expo SDK 55, React 19.2, React Native 0.83.2
- **지도**: 지도 웹 화면은 `react-kakao-maps-sdk`와 카카오맵 API 키가 필요합니다.
