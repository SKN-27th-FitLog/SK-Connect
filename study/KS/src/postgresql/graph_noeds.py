# 패키지
import json
from langchain_core.prompts import PromptTemplate
from graph_state import PGVectorStoreState
from langchain_tavily import TavilySearch

# 모듈
from pg_vectorstore import create_custom_pgvector
from utils.constants import LLM_NM, TavilySearchParams



#############################################################################
# PG Vector DB 노드 
#############################################################################
def search_vectordb_node(state: PGVectorStoreState) -> PGVectorStoreState:
    """ 벡터DB에서 사용자 질문에 대한 데이터를 조회하는 노드 """
    vectorstore = create_custom_pgvector()

    docs = vectorstore.similarity_search(state['question'], k=1)

    return {
        **state,
        "content": [doc.page_content for doc in docs],
        "source": [doc.metadata["source"] for doc in docs], # 문제 생기면 다른 방식으로 교체 
        "generation_strategy": "VectorDB",
    }

def evaluate_vectordb_node(state: PGVectorStoreState) -> PGVectorStoreState:
    """ 작성된 프롬프트를 가지고 사용자 질문이랑 답변이 얼마나 유사도를 가지는지 평가하는 노드 """
    # 프롬프트 
    prompt = PromptTemplate(
        template="""당신은 최고의 평가자 입니다. 
사용자의 질문에 대한 답변이 벡터DB의 데이터와 얼마나 일치하는지 평가해 주세요.
출력 형식은 json으로 다음과 같이 출력해 주세요.
{{
    "evaluation_result":str     # "yes" or "no"
    "evaluation_score":float    # 0~100
    "evaluation_detail":str     # 평가 이유
}}
백터DB 데이터: {contents}
사용자의 질문: {question}
"""
)
    model = LLM_NM.gpt5_4nano.value[1]
    chain = prompt | model
    result = chain.invoke({
        "question":state['question'],
        "contents":"\n".join(state['content'])
    })
    dic_result = json.loads(result.content)

    return {
        **state, 
        "evaluation_result":dic_result['evaluation_result'],
        "evaluation_score":dic_result['evaluation_score'],
        "evaluation_detail":dic_result['evaluation_detail']
    }


def rewriting_question_node(state: PGVectorStoreState) -> PGVectorStoreState:
    """ 사용자 질문을 재작성하는 노드 """
    prompt = PromptTemplate(
        template="""당신은 최고의 질문 재작성자 입니다. 
웹 조회가 잘 되도록 사용자의 질문을 재작성해 주세요.
사용자의 질문: {question}
"""
)
    model = LLM_NM.gpt5_4nano.value[1]
    chain = prompt | model
    result = chain.invoke({"question":state['question']})

    return {
        **state,
        "rewritten_question":result.content
    }

def tavily_search_node(state: PGVectorStoreState) -> PGVectorStoreState:
    """ Tavily 웹 검색 노드 """
    # 파라미터를 딕셔너리로 상수값 저장
    params = TavilySearchParams.BASE_PARAMS
    # 파라미터를 딕셔너리 상태로 그대로 넣어 실행 
    search = TavilySearch(**params)
    # 검색 실행 
    results = search.invoke({
        **state,
        "query":state['rewritten_question'],
    })

    return {
        **state,
        "content": [f"제목:{result["title"]}\n내용:{result["content"]}" for result in results["results"]],
        "source": [result["url"] for result in results["results"]],
        "generation_strategy": "Web_Search",
    }

def create_answer_node(state: PGVectorStoreState) -> PGVectorStoreState:
    """ 최종 답변을 생성하는 노드 """
    prompt = PromptTemplate(
        template="""당신은 친절한 어시스턴트 입니다. 
검색된 문서들을 기반으로 사용자의 질문에 답변을 해주세요.
만약 검색된 문서들을 이용해서 답변을 할 수 없는 경우에는 모른다고 답변해 주세요.
사용자의 질문: {question}
검색된 문서들: {contents}
"""
    )
    model = LLM_NM.gpt5_4nano.value[1]
    chain = prompt | model
    result = chain.invoke({
        "question":state['question'],
        "contents":"\n".join(state['content']),
    })

    return {
        **state,
        "answer":result.content,
        "source":state['source'],
    }
    