# SK_Connect - 이전용 번들

이 폴더의 내용을 대상 프로젝트(SK-CONNECT)의 `front/` 폴더에 복사하여 사용합니다.

## 포함 내용

- `src/` - SK_Connect 앱 소스
- `.env.example` - 환경 변수 템플릿
- `INTEGRATION.md` - App.js 연동 및 먼저 해야 할 작업
- `SETUP_GUIDE.md` - 설치 및 실행 가이드

---

## 이전 절차 체크리스트

### 1단계: 먼저 해야 할 작업

| 순서 | 작업 | 상세 |
|------|------|------|
| ☐ | **1-1. src 복사·병합** | `front-export/src/`를 `front/src/`에 복사. 기존 src가 있으면 폴더 단위로 병합 (INTEGRATION.md 1-1 참고) |
| ☐ | **1-2. App.js 수정** | 기존 `front/App.js`를 INTEGRATION.md 예시대로 수정 또는 통합 |
| ☐ | **1-3. .env 생성** | `.env.example`을 `front/.env`로 복사 후 `EXPO_PUBLIC_KAKAO_MAPS_JAVASCRIPT_KEY` 입력 |
| ☐ | **1-4. 문서 복사** | `SETUP_GUIDE.md`, `INTEGRATION.md`를 `front/`에 복사 (참고용) |

### 2단계: 의존성 설치 (front/ 내부에서)

| 순서 | 작업 | 상세 |
|------|------|------|
| ☐ | **2-1. 패키지 설치** | `front/` 폴더로 이동 후 `npm install` |
| ☐ | **2-2. 누락 패키지 추가** | `@react-navigation/*`, `react-native-safe-area-context`, `react-native-screens`, `react-kakao-maps-sdk` 없으면 `front/`에서 추가 (SETUP_GUIDE 2절) |

### 3단계: 실행 (front/ 내부에서)

| 순서 | 작업 | 상세 |
|------|------|------|
| ☐ | **3-1. 웹 실행** | `front/` 폴더에서 `npx expo start --web` |

---

## 타겟 구조 안내

SK-CONNECT의 `front/`는 **실행에 필요한 모든 것이 이미 들어 있는** 자립형 Expo 앱입니다. `assets`, `src`, `App.js`, `app.json`, `package.json` 등이 front/ 안에 있으며, 모든 설치·실행 작업은 이 폴더 안에서만 수행합니다.

**src 병합**: 기존 `front/src`에는 api, components, constants, navigation, screens가 있습니다. SK_Connect는 **config**, **lib**, **theme** 폴더를 추가하고, 공통 폴더는 파일 단위로 병합합니다. 자세한 내용은 `SETUP_GUIDE.md` 0절, `INTEGRATION.md` 1-1을 참고하세요.
