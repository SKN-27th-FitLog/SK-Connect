import json
import re
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
            selected_data = {}
            if data:
                selected_data = data[0]
            data = selected_data

        post_text = str(result.get("post") or data.get("content") or "").strip()
        if not post_text:
            return {"is_pass": False, "reason": "게시글 본문이 비어 있습니다."}

        # LLM 평가 전에 명확한 템플릿 잔여 문구는 로컬에서 빠르게 차단한다.
        banned_tokens = ["[장소 이름]", "[여기에 식당 이름]", "[참고]", "**[참고]**", "여기에", "xxxxx"]
        found_banned_tokens = [token for token in banned_tokens if token in post_text]
        if found_banned_tokens:
            return {
                "is_pass": False,
                "reason": f"템플릿/placeholder 문구가 포함되어 있습니다: {', '.join(found_banned_tokens)}",
            }

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
            - '[장소 이름]', '[참고]', '여기에', 'xxxxx' 같은 placeholder가 없는가

            반드시 아래 JSON 형식만 반환하세요. 코드블록(```json)을 붙이지 마세요.
            {{
              "is_pass": true 또는 false,
              "reason": "실패한 경우 구체적인 사유, 통과면 빈 문자열"
            }}
            """
        )
        response = llm.invoke(prompt.format(post=post_text))
        content = str(response)
        if hasattr(response, "content"):
            content = response.content
        content = content.strip()

        # 모델이 JSON 코드블록으로 감싸거나 앞뒤 설명을 붙인 경우에도 파싱 가능하게 정리한다.
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*", "", content, flags=re.IGNORECASE)
            content = re.sub(r"\s*```$", "", content).strip()

        json_match = re.search(r"\{.*\}", content, flags=re.DOTALL)
        if json_match:
            content = json_match.group(0)

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
