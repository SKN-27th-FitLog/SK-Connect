# SK_Connect 앱 연동

대상 프로젝트(SK-CONNECT)의 `front/App.js`에 SK_Connect 네비게이션을 붙이는 방법입니다. **모든 실행 및 진행 작업은 `front/` 폴더 내부에서 수행됩니다.**

---

## 1. 먼저 해야 할 작업

이전을 진행하기 **전** 또는 **직후**에 아래 작업을 수행합니다.

### 1-1. src 복사·병합

타겟 `front/src`에는 이미 `api`, `components`, `constants`, `navigation`, `screens`가 있습니다. `front-export/src/` 내용을 대상 `front/src/`에 복사합니다.

- **신규 추가** (타겟에 없는 폴더): `config/`, `lib/`, `theme/` → `front/src/`에 그대로 추가
- **병합** (타겟에 이미 있는 폴더): `api`, `components`, `constants`, `navigation`, `screens` → 파일 단위로 비교. 파일명이 겹치면 SK_Connect 쪽이 우선
- **기존 `front/src`가 비어 있거나 덮어써도 되는 경우**: `front-export/src/` 전체를 `front/src/`에 덮어쓰기

### 1-2. App.js 수정

기존 `front/App.js`를 아래 예시처럼 수정합니다. SK_Connect만 사용하는 경우 예시 코드로 교체하고, 기존 화면을 유지해야 하면 `AppNavigator`를 기존 라우팅 구조 안에 통합합니다.

### 1-3. .env 생성

`front-export/.env.example`을 `front/.env`로 복사한 뒤, 카카오맵 **JavaScript 키**를 입력합니다. 지도 탭을 사용하지 않을 경우 비워두어도 되나, 지도 화면은 동작하지 않습니다.

---

## 2. App.js 예시

```js
import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import AppNavigator from './src/navigation/AppNavigator';

export default function App() {
  return (
    <SafeAreaProvider>
      <NavigationContainer>
        <AppNavigator />
      </NavigationContainer>
    </SafeAreaProvider>
  );
}
```

---

## 3. 사전 조건

- `front/` 폴더에 `src/`가 `front/src/` 경로에 위치해야 합니다.
- 필수 의존성이 `package.json`에 포함되어 있어야 합니다. (SETUP_GUIDE.md 참고)
- `.env`에 `EXPO_PUBLIC_KAKAO_MAPS_JAVASCRIPT_KEY`가 설정되어 있어야 지도 웹 화면이 동작합니다.
