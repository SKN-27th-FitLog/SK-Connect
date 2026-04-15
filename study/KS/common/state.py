from langgraph.graph.message import add_messages
from typing import Annotated
from typing_extensions import TypedDict
from .constants import LLM_NM
from langgraph.graph import MessagesState


############################################################
# 쳇봇 용 상태 클래스 
############################################################

class ChatbotState(MessagesState):
    """
    답변 챗봇에서 사용할 상태
    """
    # 이렇게 처리해도 messages는 자동으로 추가된다고 하니 이렇게 처리 
    # messages: Annotated[list, add_messages] # 챗팅 메세지 이력데이터 
    keyword: str  # 질문에 대한 키워드
    llm: str = LLM_NM.ollama.name           # 모델 이름 