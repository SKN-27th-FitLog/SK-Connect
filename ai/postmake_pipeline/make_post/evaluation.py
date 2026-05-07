import json
import time

from common.llm_factory import get_llm
from common.logging_config import set_logging
from langchain_core.prompts import ChatPromptTemplate

logger = set_logging()


def evaluate_post_completion(result: dict) -> dict:
    """게시글 완성도를 검사하고 통과 여부와 실패 사유를 반환한다."""
    try:
        llm = get_llm()
        data = result.get("data") or {}
        if isinstance(data, list):
            data = data[0] if data else {}
        post_text = str(result.get("post") or data.get("content") or "").strip()
        if not post_text:
            return {"is_pass": False, "reason": "게시글 본문이 비어 있습니다."}

        prompt = ChatPromptTemplate.from_template(
            """
            # [SYSTEM ROLE]
            당신은 게시글 완성도 검사를 담당하는 전문가입니다.
            아래 게시글 본문을 보고 완성도를 평가하세요.

            [POST]
            평가해야 하는 게시글 내용입니다.
            {post}

            [EVALUATION RULES]
            아래 조건을 모두 만족하면 통과입니다.
            - 문장이 자연스럽고 맥락이 이어지는가
            - 최소 3문장 이상이며 내용이 충분한가
            - 지나치게 진부하거나 반복적인 표현이 없는가
            - 실제 사람이 작성한 것 같은 자연스러운 말투인가
            - 부정적인 내용으로 작성하지 않았는가

            반드시 아래 JSON 형식만 반환하세요.
            {{
              "is_pass": true 또는 false,
              "reason": "실패한 경우 구체적인 사유, 통과면 빈 문자열"
            }}
            """
        )
        response = llm.invoke(prompt.format(post=post_text))
        content = response.content if hasattr(response, "content") else str(response)
        content = content.strip()

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            return {
                "is_pass": False,
                "reason": f"평가 결과를 JSON으로 해석하지 못했습니다. 원본 응답: {content}",
            }

        return {
            "is_pass": bool(parsed.get("is_pass")),
            "reason": str(parsed.get("reason") or ""),
        }

    except Exception as e:
        data = result.get("data") or [{}]
        if isinstance(data, dict):
            data = [data]
        logger.error(f"Error={e} | time={time.time()} | crawling_id={data[0].get('crawling_id')}")
        return {"is_pass": False, "reason": str(e)}
