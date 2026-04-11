import streamlit as st
from common.llm import get_llm
from common.prompt import get_short_answer_prompt
from common.chain import build_chain
from common.members import ShortAnswerTask, OutputStyle

st.set_page_config(page_title="단답 화면", page_icon="📝")

st.title("📝 단답형 AI 도우미")
st.markdown("특정 작업(요약, 설명, 번역 등)에 대해 빠르고 정확한 답변을 제공합니다.")

# 1. UI 입력 설정
col1, col2 = st.columns(2)
with col1:
    task = st.selectbox("작업 목적", options=[t.value for t in ShortAnswerTask], index=0)
with col2:
    output_style = st.selectbox("출력 스타일", options=[s.value for s in OutputStyle], index=0)

user_input = st.text_area("질문이나 요청 사항을 입력하세요", placeholder="내용을 입력해주세요...", height=150)

# 2. 실행 로직
if st.button("🚀 실행"):
    if not user_input.strip():
        st.warning("질문을 입력해주세요.")
    else:
        # 사이드바에서 LLM 설정 로드
        config = st.session_state.get("llm_config", {})
        
        try:
            # 체인 구축
            llm = get_llm(**config)
            prompt = get_short_answer_prompt()
            chain = build_chain(llm, prompt)
            
            # 말풍선 UI를 통한 스트리밍 응답
            with st.chat_message("assistant"):
                # 프롬프트 변수 전달하여 실행
                response = st.write_stream(chain.stream({"task": task, "output_style": output_style, "user_input": user_input}))
                
        except Exception as e:
            st.error(f"오류가 발생했습니다: {str(e)}")

# 상속된 사이드바 정보 표시
st.sidebar.markdown(f"**현재 설정:**\n- Provider: {st.session_state.get('llm_config', {}).get('provider')}\n- Model: {st.session_state.get('llm_config', {}).get('model_name')}")
