from src.logging_config import set_logging
from src.node import get_llm
from langchain_core.prompts import ChatPromptTemplate
logger = set_logging()

def validate_post_completion(result: dict) -> bool:
    """게시글 완성도 검사"""
    try:
        llm = get_llm()
        prompt = ChatPromptTemplate.from_template(
            """
            # [SYSTEM ROLE]
            당신은 게시글 완성도 검사를 담당하는 전문가입니다.
            해당 게시글이 완성도가 높은지 검사해줘.
            """
        )
        response = llm.invoke(prompt.format(post=result["post"]))
        result = response.content if hasattr(response, "content") else str(response)
        return "passed" in result.lower()
    except Exception as e:
        logger.error(f"Error={e} | crawling_id={result['crawling_id']}")
        return False
