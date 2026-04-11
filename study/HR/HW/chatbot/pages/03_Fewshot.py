import streamlit as st
from common.llm import get_llm
from common.prompt import get_fewshot_prompt
from common.chain import build_chain
from common.memory import get_fewshot_examples, update_fewshot_examples

st.set_page_config(page_title="Few-shot 화면", page_icon="🎯")

st.title("🎯 Few-shot 예시 기반 AI")
st.markdown("예시를 직접 입력하여 모델이 원하는 답변 스타일이나 형식을 따르도록 유도할 수 있습니다.")

# 1. Few-shot 예시 설정 영역
with st.expander("🛠️ Few-shot 예시 설정", expanded=True):
    num_examples = st.number_input("예시 개수", min_value=1, max_value=5, value=2)
    
    # 세션 상태에서 기존 예시 로드
    current_examples = get_fewshot_examples()
    
    new_examples = []
    for i in range(num_examples):
        st.markdown(f"**예시 {i+1}**")
        col1, col2 = st.columns(2)
        
        # 범위 내에 있는 경우 기존 값 사용
        default_in = current_examples[i]["input"] if i < len(current_examples) else ""
        default_out = current_examples[i]["output"] if i < len(current_examples) else ""
        
        with col1:
            ex_in = st.text_input(f"예시 {i+1} 입력 (Input)", value=default_in, key=f"ex_in_{i}")
        with col2:
            ex_out = st.text_input(f"예시 {i+1} 출력 (Output)", value=default_out, key=f"ex_out_{i}")
        
        new_examples.append({"input": ex_in, "output": ex_out})
    
    if st.button("✅ 예시 적용 (저장)"):
        update_fewshot_examples(new_examples)
        st.success("예시가 성공적으로 세션에 저장되었습니다!")

# 2. 테스트 입력을 위한 질문 영역
st.divider()
user_query = st.text_input("테스트할 질문을 입력하세요", placeholder="포도")

if st.button("🚀 실행"):
    saved_examples = get_fewshot_examples()
    
    if not saved_examples:
        st.warning("먼저 예시를 입력하고 '적용' 버튼을 눌러주세요.")
    elif not user_query.strip():
        st.warning("질문을 입력해주세요.")
    else:
        # 예시들을 프롬프트용 텍스트 블록으로 변환
        examples_str = ""
        for i, ex in enumerate(saved_examples):
            examples_str += f"예시 {i+1}\n입력: {ex['input']}\n출력: {ex['output']}\n\n"
        
        config = st.session_state.get("llm_config", {})
        
        try:
            # 체인 구축
            llm = get_llm(**config)
            prompt = get_fewshot_prompt(examples_str)
            chain = build_chain(llm, prompt)
            
            # 말풍선 UI를 통한 스트리밍 응답
            with st.chat_message("assistant"):
                st.write_stream(chain.stream({"user_input": user_query}))
                
        except Exception as e:
            st.error(f"오류가 발생했습니다: {str(e)}")

# 현재 저장된 상태를 사이드바에 표시
if saved_examples := get_fewshot_examples():
    with st.sidebar:
        st.divider()
        st.subheader("📌 저장된 Few-shot 예시")
        for i, ex in enumerate(saved_examples):
            st.caption(f"**[{i+1}]** {ex['input']} ➔ {ex['output']}")
