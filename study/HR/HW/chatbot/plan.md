# 🤖 LangChain + Streamlit 멀티화면 LLM 앱 상세 구현 계획서

본 문서는 **chatvot** 프로젝트의 상세 구현 계획서입니다. 사용자가 3가지 주요 LLM 기능을 체험할 수 있는 멀티 화면 앱을 구축하며, Ollama와 Groq 모델을 자유롭게 선택할 수 있도록 설계합니다.

---

## 1. 프로젝트 목표

하나의 웹 앱에서 다음 3가지 핵심 기능을 제공하여 LLM의 다양한 활용 사례를 경험할 수 있도록 합니다.

1.  **단답 화면 (Single-turn)**: 프롬프트 템플릿 기반의 빠른 질의응답 및 요약.
2.  **챗봇 화면 (Multi-turn)**: 대화 맥락을 기억하는 지능형 대화 보조.
3.  **Few-shot 화면 (Example-based)**: 사용자 제공 예시를 통한 답변 스타일 및 형식 제어.

---

## 2. 핵심 요구사항

### 필수 기능
- **모델 및 파라미터 기본값**: 
    - 기본 Provider: **Groq** (사이드바에서 변경 가능)
    - Temperature: **0.1**
    - Top_p: **1.0**
    - Frequency Penalty & Presence Penalty: 적정 수준으로 자동 조정
- **UI/UX 통일**: 
    - **모든 페이지(단답, 챗봇, Few-shot)에서 말풍선(Chat Bubble) 형태의 UI**를 사용하여 AI 응답을 렌더링.
    - 모든 화면에서 **Streaming 출력** 활성화.
- **화면 구성**: Streamlit의 `pages/` 구조를 활용한 3개 화면 구성.
- **기억 기능**: `st.session_state`를 활용하여 챗봇 화면에서 대화 맥락 유지.
- **사용자 예시 입력 및 유지**: Few-shot 화면에서 작성한 예시는 다른 예시를 입력하기 전까지 세션 내에 계속 유지.

---

## 3. 프로젝트 구조 (chatvot)

Streamlit의 표준 멀티페이지 라이브러리 구조를 따릅니다.

```text
chatvot/
├── app.py                  # 메인 진입점 (사이드바 설정 및 메인 페이지)
├── requirements.txt        # 패키지 의존성
├── .env                    # 환경변수 (API 키)
├── .gitignore
├── common/                 # 공통 로직 모듈
│   ├── __init__.py
│   ├── llm.py              # LLM 인스턴스 팩토리 및 파라미터 설정
│   ├── chain.py            # LangChain LCEL 구성
│   ├── prompt.py           # 화면별 프롬프트 템플릿 관리
│   ├── memory.py           # 대화 히스토리 및 세션 관리
│   └── util.py             # 환경변수 로딩 및 공통 유틸리티
├── pages/                  # Streamlit 멀티페이지
│   ├── 01_Short_Answer.py  # 단답 화면
│   ├── 02_Chatbot.py      # 챗봇 화면
│   └── 03_Fewshot.py       # Few-shot 화면
└── assets/
    └── sample_prompts.md   # 프롬프트 예시 라이브러리
```

---

## 4. 화면별 상세 설계

### 4.1. 화면 1: 단답 화면 (Single-turn)
- **목적**: 이전 대화와 무관하게 특정 작업(요약, 번역 등)에 집중.
- **입력 요소**:
    - Task 선택 (개념 설명, 요약, 추출 등)
    - Output Style 선택 (쉽게, 자세히, 마크다운 등)
    - User Question 입력창
- **프롬프트 전략**: `ChatPromptTemplate`을 사용하여 시스템 지침과 사용자 입력을 명확히 구분.

### 4.2. 화면 2: 챗봇 화면 (Multi-turn)
- **UI**: 말풍선 형태의 대화 UI (`st.chat_message`) 기본 적용.
- **기억 방식**: 세션 기반 메시지 리스트 관리.

### 4.3. 화면 3: Few-shot 화면 (Example-based)
- **목적**: 소량의 예시를 통해 모델에게 원하는 출력 형식을 가이드.
- **입력 요소**:
    - 예시 개수 설정 (1~3개)
    - 각 예시의 입력(Input) 및 출력(Output) 텍스트 박스
    - 테스트할 사용자 입력(Query)
- **데이터 유지 로직**:
    - 사용자가 입력한 예시들은 `st.session_state["fewshot_examples"]`에 저장됨.
    - **새로운 예시를 입력하고 '적용'하지 않는 한, 이전에 입력했던 예시가 유지**되어 여러 번의 Query 테스트에 재사용됨.
- **프롬프트 전략**: 저장된 예시들을 `FewShotChatMessagePromptTemplate` 형태로 가공하여 최종 프롬프트 구성.

---

## 5. 모델 연동 및 모듈 상세

### 5.1. `common/llm.py`
- 기본값 설정: Provider=`Groq`, Temp=`0.1`, Top_p=`1.0`.
- Penalty 파라미터(`frequency_penalty`, `presence_penalty`) 조정 기능 포함.

### 5.2. `common/memory.py`
- 화면별 독립 세션 관리 및 Few-shot 예시 보존 로직.

---

## 6. 예외 처리 및 UX 고려사항

- **Rate Limit**: Groq의 무료 티어 제한(429 Error) 발생 시 사용자에게 알림 및 재시도 안내.
- **Streaming**: 모든 응답에 일관되게 적용하여 "생각 중" UX 구현.

---

## 7. 구현 단계 (Task Checklist)

### Phase 1. 환경 구성
- [ ] 디렉토리 구조 생성 및 환경변수 세팅

### Phase 2. 핵심 로직 (`common/`)
- [ ] `llm.py`: Ollama/Groq 연동 및 에러 처리
- [ ] `prompt.py`: 3가지 화면용 베이스 프롬프트 정의
- [ ] `memory.py`: 세션 기반 히스토리 및 **Few-shot 예시 보존 로직** 구현

### Phase 3. 페이지 구현 (`pages/`)
- [ ] `01_Short_Answer.py`: 템플릿 기반 UI 및 실행 로직
- [ ] `02_Chatbot.py`: 멀티턴 메시지 렌더링 및 메모리 연동
- [ ] `03_Fewshot.py`: **예시 유지(Persistence) 기능**이 포함된 입력 폼 및 프롬프트 조합

### Phase 4. 메인 앱 (`app.py`)
- [ ] 사이드바 공통 설정 (모델, 온도, 초기화 버튼)
- [ ] 메인 홈 화면 설명 및 프로젝트 가이드 표시

---

## 8. 실행 방법

1.  **의존성 설치**: `pip install -r requirements.txt`
2.  **Ollama**: 로컬에서 Ollama 실행 및 모델 다운로드 (`ollama pull gemma3:4b`)
3.  **환경변수**: `.env` 파일에 `GROQ_API_KEY` 입력
4.  **앱 실행**: `streamlit run app.py`
