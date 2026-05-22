import json
import re
import time

from common.llm_factory import get_evaluation_llm
from common.logging_config import set_logging
from langchain_core.prompts import ChatPromptTemplate

logger = set_logging()


# 한 source row에서 평가에 넣을 최대 글자 수 (프롬프트 비용/길이 제어)
_MAX_SOURCE_CHARS_PER_ROW = 600
# 평가 프롬프트에 같이 보낼 source row 최대 개수
_MAX_SOURCE_ROWS = 12
_GENERIC_CLICHE_PHRASES = (
    "좋은 시간을 보냈",
    "만족스러웠",
    "만족스러운",
    "기분 좋게",
    "다음에 또",
    "다시 찾고 싶은",
    "추천하고 싶은",
    "한 번쯤",
    "잘 어울렸",
    "인상적이었",
    "기억에 남",
    "매력적이었",
)


def evaluate_post_completion(result: dict) -> dict:
    """게시글 완성도를 검사하고 통과 여부와 실패 사유를 반환한다."""
    try:
        llm = get_evaluation_llm()
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

        for line in post_text.splitlines():
            line_text = str(line or "").strip()
            compact_line = re.sub(r"[\s\*\[\]\(\){}<>:：`\"'“”‘’]+", "", line_text)
            meta_hit_count = sum(
                1 for marker in (
                    "참고",
                    "요청하신",
                    "형식",
                    "예시",
                    "실제사용",
                    "사용하실때",
                    "톤앤매너",
                    "수정하시면",
                    "작성된",
                    "위내용",
                )
                if marker in compact_line
            )
            if meta_hit_count >= 2:
                return {
                    "is_pass": False,
                    "reason": f"본문 외 메타 안내문이 포함되어 있습니다: {line_text[:80]}",
                }

        local_quality_issue = None
        awkward_phrase = "갈 때까지도"
        for match in re.finditer(re.escape(awkward_phrase), post_text):
            before = post_text[:match.start()].rstrip()
            previous_word = before.split()[-1] if before.split() else ""
            if (
                not previous_word
                or previous_word in {"그리고", "또", "또한", "그래도"}
                or previous_word.endswith((".", "!", "?", "。", "！", "？"))
            ):
                local_quality_issue = (
                    "'갈 때까지도'는 목적지나 재방문 맥락 없이 쓰여 어색합니다. "
                    "'다시 갈 때까지' 또는 '돌아오는 길에도'처럼 고쳐야 합니다."
                )
                break

        if not local_quality_issue:
            compact_text = re.sub(r"\s+", " ", post_text)
            cliche_hits = [
                phrase for phrase in _GENERIC_CLICHE_PHRASES
                if phrase in compact_text
            ]
            repeated_cliches = [
                phrase for phrase in _GENERIC_CLICHE_PHRASES
                if compact_text.count(phrase) >= 2
            ]
            if repeated_cliches:
                local_quality_issue = f"상투적인 표현이 반복됩니다: {', '.join(repeated_cliches[:3])}"
            elif len(cliche_hits) >= 4:
                local_quality_issue = f"상투적인 표현이 너무 많습니다: {', '.join(cliche_hits[:4])}"

        if local_quality_issue:
            return {
                "is_pass": False,
                "reason": local_quality_issue,
            }

        visible_post_text = re.sub(r"(?is)<[^>]+>", " ", post_text)
        visible_post_text = re.sub(r"https?://\S+", " ", visible_post_text)
        visible_post_text = re.sub(r"\s+", " ", visible_post_text).strip()
        sentence_parts = [
            sentence.strip()
            for sentence in re.split(
                r"(?:[.!?。！？]+|\n+|(?<=[가-힣])(다|요|죠|임|함|네|음|됨|였다|했다|었다|았다|더라|더라고요|습니다|네요|어요|아요|예요|이에요)(?=\s|$))",
                visible_post_text,
            )
            if sentence and len(sentence.strip()) >= 8
        ]
        if len(visible_post_text) < 180 or len(sentence_parts) < 3:
            logger.warning(
                f"local evaluation short text | chars={len(visible_post_text)} | "
                f"sentences={len(sentence_parts)} | preview={visible_post_text[:160]}"
            )
            return {
                "is_pass": False,
                "reason": (
                    "본문 텍스트가 부족합니다. 이미지/링크를 제외하고 "
                    f"{len(visible_post_text)}자, {len(sentence_parts)}문장입니다."
                ),
            }

        # 원본 리뷰(grounding 근거)를 모아 LLM 평가에 함께 넘긴다.
        source_data = result.get("data") or []
        if isinstance(source_data, dict):
            source_data = [source_data]

        source_texts: list[str] = []
        for row in source_data:
            if not isinstance(row, dict):
                continue
            title = str(
                row.get("shop_name")
                or row.get("shop_nm")
                or row.get("store_name")
                or row.get("restaurant_name")
                or row.get("title")
                or ""
            ).strip()
            content = str(row.get("content") or "").strip()
            if not title and not content:
                continue
            if len(content) > _MAX_SOURCE_CHARS_PER_ROW:
                content = content[:_MAX_SOURCE_CHARS_PER_ROW] + "..."
            source_parts = []
            if title:
                source_parts.append(f"title/shop_name: {title}")
                if title.lower().startswith("review -"):
                    cleaned_title = title.split("-", 1)[1].strip()
                    if cleaned_title:
                        source_parts.append(f"shop_name_alias: {cleaned_title}")
            if content:
                source_parts.append(f"review: {content}")
            source_texts.append(" | ".join(source_parts))
            if len(source_texts) >= _MAX_SOURCE_ROWS:
                break

        if source_texts:
            sources_block = "\n".join(
                f"[{idx}] {text}"
                for idx, text in enumerate(source_texts, start=1)
            )
        else:
            sources_block = "(원본 리뷰 없음)"

        prompt = ChatPromptTemplate.from_template(
            """
            # [SYSTEM ROLE]
            당신은 게시글 완성도와 사실성(grounding)을 함께 검사하는 전문가입니다.
            아래 게시글 본문(POST)을 [SOURCES]의 원본 리뷰들에 비추어 평가하세요.

            [SOURCES]
            게시글이 근거로 삼아야 하는 원본 리뷰 모음입니다.
            각 source의 title/shop_name/shop_name_alias는 가게명 또는 장소명 grounding으로 인정하세요.
            단, title/shop_name은 가게명 grounding에만 사용할 수 있고 메뉴명, 가격, 주차, 웨이팅, 서비스 같은 세부 사실의 근거로 쓰면 안 됩니다.
            게시글의 사실(메뉴명, 재료, 평가 포인트 등)은 이 안에서 직접적으로 등장하거나
            자연스럽게 추론 가능해야 합니다.
            {sources}

            [POST]
            평가해야 하는 게시글 내용입니다.
            {post}

            [EVALUATION RULES]
            아래 조건을 **모두 만족**하면 통과입니다. 하나라도 어기면 fail.
            1. 문장이 자연스럽고 맥락이 이어지는가
            2. 최소 3문장 이상이며 내용이 충분한가
            3. 지나치게 진부하거나 반복적인 표현이 없는가
            4. 실제 사람이 작성한 것 같은 자연스러운 말투인가
            5. 부정적인 내용으로 작성하지 않았는가
            6. '[장소 이름]', '[참고]', '여기에', 'xxxxx' 같은 placeholder나 본문 밖 메타 안내문이 없는가
               - "요청하신 형식", "작성된 예시", "실제 사용하실 때", "톤앤매너", "수정하시면 됩니다"처럼 작성물 자체를 설명하는 문장은 fail.
            7. **(GROUNDING)** POST에 등장하는 메뉴명, 재료, 고유명사, 특정 수식어가
               [SOURCES]에 등장하거나 자연스럽게 추론 가능해야 한다.
               - SOURCES에 한 번도 나오지 않는 고유명사·메뉴명·재료명·지명이 POST에 나오면 fail.
            8. **(MEANING)** 일반 독자가 쉽게 의미를 파악할 수 없는 다음 표현이 있으면 fail:
               - 흔하지 않은 한자어/줄임말 (예: "오신" 같은 단어가 풀이 없이 등장)
               - 사전 의미가 모호하거나 문맥상 어색하게 잘려있는 단어
               - 추상적 한 글자/두 글자 한자어가 음식·서비스 평가 맥락에서 단독으로 쓰인 경우
               단, SOURCES에 같은 표현이 그대로 등장한다면 통과로 본다.
            9. **(SPECIFICITY)** SOURCES나 키워드에서 확인 가능한 구체적인 대상과 평가가 최소 2개 이상 드러나야 한다.
               - 메뉴명, 재료, 식감, 양, 가격, 서비스, 매장 분위기처럼 무엇이 왜 좋았는지 알 수 있어야 한다.
               - "맛있다", "좋았다", "만족스러웠다"처럼 어느 식당에도 붙일 수 있는 표현만 있으면 fail.
            10. **(CLICHE)** 상투적인 칭찬이나 템플릿 같은 문장이 많으면 fail.
               - 같은 의미의 칭찬을 반복하거나, SOURCES를 보지 않아도 쓸 수 있는 일반 문장 위주면 fail.

            [실패 사유 작성 가이드]
            - rule 7 위반: "SOURCES에 없는 표현: <단어>" 형태로 명시
            - rule 8 위반: "독자가 의미를 알기 어려운 표현: <단어>" 형태로 명시
            - rule 9 위반: "구체성 부족: <부족한 부분>" 형태로 명시
            - rule 10 위반: "상투적 표현 과다: <반복/진부한 표현>" 형태로 명시

            반드시 아래 JSON 형식만 반환하세요. 코드블록을 붙이지 마세요.
            {{
              "is_pass": true 또는 false,
              "reason": "실패한 경우 구체적인 사유, 통과면 빈 문자열"
            }}
            """
        )
        response = llm.invoke(prompt.format(post=post_text, sources=sources_block))
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
