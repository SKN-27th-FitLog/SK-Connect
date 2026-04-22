# 패키지 설치
import os

import streamlit as st

from common.utils.constants import LLM_NM


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
        model = st.selectbox('Model', list(LLM_NM.__members__.keys()))

    return model 
