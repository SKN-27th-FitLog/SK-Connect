# 패키지
import time 

# 모듈
from .chains import get_chain

# LLM 관련 라이브러리 
from langgraph.graph.message import add_messages
from typing import Annotated
from typing_extensions import TypedDict

##########################################################################################
# LangGraph
##########################################################################################

# 챗봇 스테이트 클래스 
class ChatbotState(TypedDict):
    '''
    해당 state는 langgraph 에서 사용할 챗봇의 스테이트 클래스이다. 
    해당 클래스는 쳇봇 실행 시 기본적으로 필요한 정보를 가지게 되며 실행 후 결과 값도 같이 가지고 있게 된다. 
    해당 클래스는 다음과 같은 정보를 가진다. 
    입력정보:
    - llm : 해당 체인이 사용할 모델 이름 (기본값: ollama)
    - chat_type : 체인에서 사용하는 프롬프트 설정용 채팅 타입 (기본값: 일반)
    - user_msg : 사용자가 입력한 채팅 메시지 

    출력정보:
    - result : 체인 실행 결과 값 (체인 실항하고 나서 답변 객체가 결과 값으로 전달된다. 체인에 파서가 붙어 있으므로 적절한 파서에 따라 결과 값이 리턴되게 된다. )
    '''
    llm: str = 'ollama' # 모델 이름 
    chat_type: str = '일반' # 체인 내부에서 사용할 채팅 타입
    user_msg:str = ''  # 사용자가 입력한 메시지 
    messages: Annotated[list, add_messages] # 체인 실행 결과 값 


def chat_node(state: ChatbotState):
    """
    LLM과 대화하는 노드입니다.
    입력: 현재 상태(메시지들)
    출력: LLM의 응답이 추가된 새로운 상태
    """

    
    # LLM에게 질문하고 답변 받기
    response = llm.invoke(state["messages"])
    
    print(f"AI 응답: {response.content}")
    
    # 새로운 메시지를 상태에 추가해서 반환
    # ad_messages에 의해서 기존 messages에 새로운 response가 추가됨 
    return {"messages": [response]}


##########################################################################################
# 함수 정의 
##########################################################################################








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