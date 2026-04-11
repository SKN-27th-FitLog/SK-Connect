from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableSerializable

def build_chain(llm: BaseChatModel, prompt: ChatPromptTemplate) -> RunnableSerializable:
    """
    단순 LCEL 체인을 구축합니다: 프롬프트 | LLM | 출력 파서.
    """
    return prompt | llm | StrOutputParser()
