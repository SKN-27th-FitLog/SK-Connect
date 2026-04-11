import streamlit as st
from common.llm import get_llm
from common.prompt import get_chatbot_prompt
from common.chain import build_chain
from common.memory import add_message

st.set_page_config(page_title="챗봇 화면", page_icon="💬")

st.title("💬 멀티턴 AI 챗봇")
st.markdown("이전 대화 내용을 기억하여 문맥에 맞는 대화를 이어갑니다.")

# 1. 초기화 및 사이드바 설정
config = st.session_state.get("llm_config", {})
history = st.session_state.get("chat_history", [])

# 기존 메시지 렌더링
for msg in history:
    role = "user" if msg.type == "human" else "assistant"
    with st.chat_message(role):
        st.markdown(msg.content)

# 2. 채팅 입력 처리
if user_input := st.chat_input("메시지를 입력하세요..."):
    # 사용자 메시지 표시
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # 히스토리에 추가
    add_message("user", user_input)
    
    try:
        # 체인 구축
        llm = get_llm(**config)
        prompt = get_chatbot_prompt()
        chain = build_chain(llm, prompt)
        
        # AI 응답 (스트리밍)
        with st.chat_message("assistant"):
            # 현재 입력값은 프롬프트에서 별도로 처리하므로 직전까지의 히스토리 전달
            response_text = st.write_stream(chain.stream({
                "chat_history": st.session_state["chat_history"][:-1],
                "user_input": user_input
            }))
            
            # 히스토리에 응답 추가
            add_message("assistant", response_text)
            
    except Exception as e:
        st.error(f"오류가 발생했습니다: {str(e)}")

# 사이드바 정보 표시
st.sidebar.markdown(f"**현재 설정:**\n- Provider: {config.get('provider')}\n- Model: {config.get('model_name')}")
