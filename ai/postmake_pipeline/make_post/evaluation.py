from common.logging_config import set_logging
from langchain_core.prompts import ChatPromptTemplate
from common.llm_factory import get_llm
import time
logger = set_logging()

def evaluate_post_completion(result: dict) -> str:
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

            
            [POST]
            평가해야 하는 게시글 내용입니다.
            {post}


            평가 내용은 각 항목별로 작성해주세요.
            - 문장이 자연스럽고 맥락이 이어지는가
            - 최소 3문장 이상이며 내용이 충분한가
            - 지나치게 짧거나 의미 없는 반복이 없는가
            - 사람이 작성한 것 같은 느낌을 주는가

            """
        )
        response = llm.invoke(prompt.format(post=post_text)) # LLM 실행
        return response.content
            
    except Exception as e:
        data = result.get("data") or [{}]
        logger.error(f"Error={e} | time={time.time()} | crawling_id={data[0].get('crawling_id')}")
        return ""
