from langgraph.graph.message import add_messages
from typing import Annotated
from typing_extensions import TypedDict
from .constants import LLM_NM

class ChatbotState(TypedDict):
    """
    답변 챗봇에서 사용할 상태
    """
    messages: Annotated[list, add_messages] # 챗팅 메세지 이력데이터 
    keyword: str  # 질문에 대한 키워드
    llm: str = LLM_NM.ollama.name           # 모델 이름 