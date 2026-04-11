import time 

from .chains import get_chain

def get_msg_from_llm(llm_nm:str='ollama',chat_type:str='일반', user_msg:str=''):
    '''
    사용자의 msg 받으면, llm 답변하는 함수
    - llm_nm: 모델 종류
    - chat_type: 채팅 타입
    - user_msg: 현재 사용자가 궁금한 질문 
    - hist_messages: 과거의 대화 리스트(사용자 질문 & AI 답변)
    '''

    # 체인
    chain = get_chain(llm_nm, chat_type)

    # 답변 응답 (invoke -> stream)
    for chunk in chain.stream({'question': user_msg }):
        yield chunk
        time.sleep(0.05)