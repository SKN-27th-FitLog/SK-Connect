import streamlit as st
from common.util import load_env_vars
from common.memory import init_session_state, clear_chat_history
from common.members import LLMProvider

# 1. 페이지 설정
st.set_page_config(
    page_title="chatvot - 멀티 LLM 앱",
    page_icon="🤖",
    layout="wide",
)

# 2. 초기화
load_env_vars()
init_session_state()

# 3. 사이드바 설정
st.sidebar.title("⚙️ LLM 설정")

# 제공자 선택 (Enum 기반, 기본값 Groq)
provider = st.sidebar.selectbox(
    "Provider 선택",
    options=[p.value for p in LLMProvider],
    index=0
)

# 제공자별 모델 선택
if provider == LLMProvider.GROQ.value:
    model_name = st.sidebar.selectbox(
        "Model 선택",
        options=[
            "llama-3.3-70b-versatile",
            "llama3-8b-8192",
            "mixtral-8x7b-32768",
            "llama-3.1-8b-instant"
        ],
        index=0
    )
else:
    model_name = st.sidebar.text_input("Ollama 모델명 입력", value="gemma3:4b")

# 하이퍼파라미터 설정
st.sidebar.divider()
st.sidebar.subheader("하이퍼파라미터")
temperature = st.sidebar.slider("Temperature", min_value=0.0, max_value=2.0, value=0.1, step=0.1)
top_p = st.sidebar.slider("Top P", min_value=0.0, max_value=1.0, value=1.0, step=0.05)
frequency_penalty = st.sidebar.slider("Frequency Penalty", min_value=-2.0, max_value=2.0, value=0.0, step=0.1)
presence_penalty = st.sidebar.slider("Presence Penalty", min_value=-2.0, max_value=2.0, value=0.0, step=0.1)

# 세션 상태에 저장하여 페이지 간 공유
st.session_state["llm_config"] = {
    "provider": provider,
    "model_name": model_name,
    "temperature": temperature,
    "top_p": top_p,
    "frequency_penalty": frequency_penalty,
    "presence_penalty": presence_penalty,
}

# 사이드바 버튼
st.sidebar.divider()
if st.sidebar.button("🗑️ 대화 기록 초기화"):
    clear_chat_history()
    st.sidebar.success("대화 기록이 초기화되었습니다.")

# 4. 메인 홈 화면
st.title("🤖 chatvot: 멀티화면 LLM 앱")
st.markdown("""
이 앱은 **LangChain**과 **Streamlit**을 활용하여 제작된 멀티 LLM 체험 도구입니다.
왼쪽 네비게이션 메뉴를 통해 다양한 AI 기능을 체험해보세요!

### 🌟 주요 기능
1. **단답 화면**: 특정 작업에 대해 빠르게 답변을 받는 화면입니다.
2. **챗봇 화면**: 이전 대화 맥락을 기억하는 멀티턴 대화 화면입니다.
3. **Few-shot 화면**: 예시를 작성하여 원하는 답변 형식을 유도하는 화면입니다.

---
### 🛠️ 시작 가이드
1. 사이드바에서 원하는 **Provider(Groq/Ollama)**와 **모델**을 선택하세요.
2. 하이퍼파라미터를 조정하여 답변의 창의성이나 스타일을 조절할 수 있습니다. (기본값: Temp 0.1)
3. 사이드바의 **네비게이션**을 통해 원하는 메뉴로 이동하여 AI와 대화해보세요.
""")

st.info("💡 사이드바에서 각 옵션을 설정하면 모든 페이지에 공통으로 적용됩니다.")
