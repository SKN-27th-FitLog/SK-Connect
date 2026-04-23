# 패키지 
from typing_extensions import TypedDict
from typing import Annotated

# LangGraph 라이브러리 
from langgraph.graph.message import add_messages


#################################################
# 채팅 상태 관리 클래스
#################################################
class ChatbotState(TypedDict):
    '''
    langgraph에 저장될 데이터 객체 클래스 
    parameters:
    - messages: 채팅 내용 (add_messages로 채팅 내용 누적됨 )
    - model: 모델 이름
    - keyword: 유저 질문에 대한 
    '''
    messages: Annotated[list[dict], add_messages]
    keyword: str         # 질문에 대한 키워드
    model: str           # 모델 이름 
