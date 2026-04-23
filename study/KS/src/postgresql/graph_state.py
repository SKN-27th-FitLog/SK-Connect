# 패키지 
from typing_extensions import TypedDict
from typing import List, Dict, Any



#################################################
# PG VectorStore Graph State 
#################################################
class PGVectorStoreState(TypedDict):
    """ PG VectorStore Graph State 
    PG VectorStore의 LangGraph에서 사용할 상태 정보 저장 
    """
    # 사용자 질문 
    question: str 
    # 조회된 문서 리스트 
    content: List[str]   
    source: List[Dict[str, Any]]
    # VectorDB의 조회 결과 평가 
    evaluation_result: str
    evaluation_score: float
    evaluation_detail: str
    # 재질문
    rewritten_question: str
    # 최종답변
    answer: str
    generation_strategy: str