# 패키지 설치
import os

import streamlit as st

from common.constants import LLM_NM


###################################################
# 사이드바 컴포넌트 
###################################################

def chatbot_sidebar():
    '''
    app.py 화면에서 사용할 사이드바 컴포넌트
    사이드 바에서 설정한 메뉴 값을 반환함 
    '''
    with st.sidebar:
        st.title('Setup')
        llm = st.selectbox('Model', list(LLM_NM.__members__.keys()))

        if os.getenv("SHOW_DB_DEBUG", "").lower() in ("1", "true", "yes"):
            from common.secure import get_checkpoint_table_counts

            with st.expander("PostgreSQL 체크포인트 (디버그)", expanded=False):
                try:
                    counts = get_checkpoint_table_counts()
                    st.json(counts)
                    st.caption(
                        "LangGraph는 `checkpoints` / `checkpoint_blobs` / `checkpoint_writes`에 저장합니다. "
                        "`user_chat_history`는 이 프로젝트 스크립트용 예시 테이블이며 앱이 자동으로 채우지 않습니다."
                    )
                except Exception as e:
                    st.error(str(e))

    return llm # 선택한 llm 객체 반환
