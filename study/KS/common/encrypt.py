import streamlit as st


#####################################################################################
# 암호화된 직렬화 객체 생성 함수 
#####################################################################################

# 캐시 리소스 데코레이터 적용(함수 호출 결과를 캐시에 저장)
@st.cache_resource 
def get_encrypted_serde():
    # LANGGRAPH_AES_KEY는 이 함수 호출 전에 이미 설정되어 있어야 함
    from langgraph.checkpoint.serde.encrypted import EncryptedSerializer
    return EncryptedSerializer.from_pycryptodome_aes()