from .state import ChatbotState
from .constants import PROMPT_NM, LLM_NM, PARSER_NM
from .chains import create_chain
from .llm import get_llm, get_parser, get_prompt


def create_keyword_node(state: ChatbotState)-> ChatbotState:
    """사용자 질문을 바탕으로 키워드 체인 생성"""
    keyword_chain = (
        get_prompt(PROMPT_NM.keyword.name) 
        | get_llm(state['llm']) 
        | get_parser(PARSER_NM.output_str.name)
    )
    question = state['messages'][-1].content
    keyword = keyword_chain.invoke({'question': question})
    return {**state, "keyword": keyword, } 

def create_coding_node(state: ChatbotState)-> ChatbotState:
    """사용자 질문을 바탕으로 코딩 체인 생성  """
    coding_chain = create_chain(state['llm'], PROMPT_NM.coding.name, PARSER_NM.output_str.name)
    question = state['messages'][-1].content
    messages = [coding_chain.invoke({'question': question})]
    return {**state, "messages": messages}

def create_cooking_node(state: ChatbotState)-> ChatbotState:
    """사용자 질문을 바탕으로 쿠킹 체인 생성  """
    cooking_chain = create_chain(state['llm'], PROMPT_NM.cooking.name, PARSER_NM.output_str.name)
    question = state['messages'][-1].content
    messages = [cooking_chain.invoke({'question': question})]
    return {**state, "messages": messages}

def create_general_node(state: ChatbotState)-> ChatbotState:
    """사용자 질문을 바탕으로 일반 체인 생성  """
    general_chain = create_chain(state['llm'], PROMPT_NM.general.name, PARSER_NM.output_str.name)
    question = state['messages'][-1].content
    messages = [general_chain.invoke({'question': question})]
    return {**state, "messages": messages}
