from common.logging_config import set_logging
from langchain_core.prompts import ChatPromptTemplate
from common.llm_factory import get_llm
logger = set_logging()

def evaluate_post_completion(result: dict) -> bool:
    """게시글 완성도 검사"""
    try:
        llm = get_llm()
        post_text = str(result.get("post") or result.get("data", {}).get("content") or "").strip() # 게시글 본문 가져오기
        if not post_text: # 게시글 본문이 없으면 실패
            return False
        prompt = ChatPromptTemplate.from_template(
            """
            # [SYSTEM ROLE]
            당신은 게시글 완성도 검사를 담당하는 전문가입니다.
            아래 게시글 본문을 보고 완성도를 평가하세요.
            기준:
            - 문장이 자연스럽고 맥락이 이어지는가
            - 최소 3문장 이상이며 내용이 충분한가
            - 지나치게 짧거나 의미 없는 반복이 없는가

            출력은 반드시 `passed` 또는 `failed` 중 하나만 반환하세요.

            [POST]
            {post}
            """
        )
        response = llm.invoke(prompt.format(post=post_text)) # LLM 실행
        verdict = response.content if hasattr(response, "content") else str(response) # 결과 가져오기
        return verdict.strip().lower() == "passed"
    except Exception as e:
        crawling_id = result.get("data", {}).get("crawling_id")
        logger.error(f"Error={e} | crawling_id={crawling_id}")
        return False
