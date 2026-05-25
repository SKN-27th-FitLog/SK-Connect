import copy
import json
import re
import time

from common.llm_factory import get_evaluation_llm
from common.logging_config import set_logging
from langchain_core.prompts import ChatPromptTemplate
from make_post.prompt import (
    EVALUATION_PROMPT_TEMPLATE,
    LINE_COMPACT_PATTERN,
    META_MARKERS,
    REVIEW_TITLE_PREFIX,
)

logger = set_logging()


# ──────────────────────────────────────────────
# 평가 규칙 설정
# ──────────────────────────────────────────────

_EVALUATION_DEFAULTS = {
    "source": {
        "max_chars_per_row": 600,
        "max_rows": 12,
        "title_keys": (
            "shop_name",
            "shop_nm",
            "store_name",
            "restaurant_name",
            "title",
        ),
        "content_key": "content",
        "review_title_prefix": REVIEW_TITLE_PREFIX,
        "empty_text": "(원본 리뷰 없음)",
    },
    "local": {
        "min_visible_chars": 180,
        "min_sentence_count": 3,
        "min_sentence_chars": 8,
        "banned_tokens": (
            "[장소 이름]",
            "[여기에 식당 이름]",
            "[참고]",
            "**[참고]**",
            "여기에",
            "xxxxx",
        ),
        "meta_markers": META_MARKERS,
        "meta_min_hits": 2,
        "cliche_phrases": (
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
        ),
        "max_cliche_hits": 4,
        "repeat_cliche_threshold": 2,
        "awkward_phrases": {
            "갈 때까지도": {
                "invalid_previous_words": ("그리고", "또", "또한", "그래도"),
                "sentence_endings": (".", "!", "?", "。", "！", "？"),
                "message": (
                    "'갈 때까지도'는 목적지나 재방문 맥락 없이 쓰여 어색합니다. "
                    "'다시 갈 때까지' 또는 '돌아오는 길에도'처럼 고쳐야 합니다."
                ),
            }
        },
    },
    "regex": {
        "line_compact": LINE_COMPACT_PATTERN,
        "html": r"(?is)<[^>]+>",
        "url": r"https?://\S+",
        "space": r"\s+",
        "sentence_split": (
            r"(?:[.!?。！？]+|\n+|"
            r"(?<=[가-힣])"
            r"(다|요|죠|임|함|네|음|됨|였다|했다|었다|았다|더라|더라고요|습니다|네요|어요|아요|예요|이에요)"
            r"(?=\s|$))"
        ),
    },
}


def _get_evaluation_rules(custom_rules: dict | None = None) -> dict:
    """기본 평가 설정에 호출부에서 넘긴 설정을 덮어쓴다."""
    rules = copy.deepcopy(_EVALUATION_DEFAULTS)
    if not custom_rules:
        return rules
    for key, value in custom_rules.items():
        if isinstance(value, dict) and isinstance(rules.get(key), dict):
            rules[key].update(value)
        else:
            rules[key] = value
    return rules


# ──────────────────────────────────────────────
# 평가 헬퍼
# ──────────────────────────────────────────────

def _find_local_quality_issue(post_text: str, rules: dict) -> str | None:
    """LLM 호출 전에 정규식/문구 기반으로 확실한 품질 문제를 먼저 잡는다."""
    local_rules = rules["local"]

    for phrase, phrase_rules in local_rules["awkward_phrases"].items():
        for match in re.finditer(re.escape(phrase), post_text):
            before = post_text[:match.start()].rstrip()
            previous_word = before.split()[-1] if before.split() else ""
            invalid_previous_words = set(phrase_rules.get("invalid_previous_words") or ())
            sentence_endings = tuple(phrase_rules.get("sentence_endings") or ())
            if (
                not previous_word
                or previous_word in invalid_previous_words
                or previous_word.endswith(sentence_endings)
            ):
                return phrase_rules.get("message") or f"'{phrase}' 문맥이 어색합니다."

    compact_text = re.sub(rules["regex"]["space"], " ", post_text)
    cliche_phrases = local_rules["cliche_phrases"]
    repeated_cliches = [
        phrase
        for phrase in cliche_phrases
        if compact_text.count(phrase) >= local_rules["repeat_cliche_threshold"]
    ]
    if repeated_cliches:
        return f"상투적인 표현이 반복됩니다: {', '.join(repeated_cliches[:3])}"

    cliche_hits = [phrase for phrase in cliche_phrases if phrase in compact_text]
    if len(cliche_hits) >= local_rules["max_cliche_hits"]:
        return f"상투적인 표현이 너무 많습니다: {', '.join(cliche_hits[:4])}"

    return None


def _build_sources_block(data_rows: list[dict], rules: dict) -> str:
    """평가 프롬프트에 넣을 원본 리뷰 블록을 만든다."""
    source_rules = rules["source"]
    source_texts: list[str] = []

    for row in data_rows:
        if not isinstance(row, dict):
            continue

        title = ""
        for key in source_rules["title_keys"]:
            value = str(row.get(key) or "").strip()
            if value:
                title = value
                break

        content = str(row.get(source_rules["content_key"]) or "").strip()
        if not title and not content:
            continue

        if len(content) > source_rules["max_chars_per_row"]:
            content = content[:source_rules["max_chars_per_row"]] + "..."

        source_parts = []
        if title:
            source_parts.append(f"title/shop_name: {title}")
            title_prefix = source_rules["review_title_prefix"]
            if title.lower().startswith(title_prefix):
                cleaned_title = title.split("-", 1)[1].strip()
                if cleaned_title:
                    source_parts.append(f"shop_name_alias: {cleaned_title}")
        if content:
            source_parts.append(f"review: {content}")

        source_texts.append(" | ".join(source_parts))
        if len(source_texts) >= source_rules["max_rows"]:
            break

    if not source_texts:
        return source_rules["empty_text"]

    return "\n".join(
        f"[{idx}] {text}"
        for idx, text in enumerate(source_texts, start=1)
    )


def _parse_llm_evaluation_response(response) -> dict:
    """LLM 응답에서 JSON만 추출해 평가 결과 dict로 변환한다."""
    content = response.content if hasattr(response, "content") else str(response)
    content = str(content).strip()

    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content, flags=re.IGNORECASE)
        content = re.sub(r"\s*```$", "", content).strip()

    json_match = re.search(r"\{.*\}", content, flags=re.DOTALL)
    if json_match:
        content = json_match.group(0)

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        compact_content = re.sub(r"\s+", " ", content).strip().lower()
        pass_markers = ("통과", "pass", "passed")
        fail_markers = ("실패", "fail", "failed")
        has_pass_marker = any(marker in compact_content for marker in pass_markers)
        has_fail_marker = any(marker in compact_content for marker in fail_markers)
        if has_pass_marker and not has_fail_marker:
            logger.warning(f"evaluation non-json pass fallback | response={content[:300]}")
            return {
                "is_pass": True,
                "reason": "",
            }
        return {
            "is_pass": False,
            "reason": f"평가 결과를 JSON으로 해석하지 못했습니다. 원본 응답: {content}",
        }

    return {
        "is_pass": bool(parsed.get("is_pass")),
        "reason": str(parsed.get("reason") or ""),
    }


# ──────────────────────────────────────────────
# 평가 진입점
# ──────────────────────────────────────────────

def evaluate_post_completion(state: dict, custom_rules: dict | None = None) -> dict:
    """게시글 완성도를 검사하고 통과 여부와 실패 사유를 반환한다."""
    try:
        rules = _get_evaluation_rules(custom_rules)

        # data_rows: 원본 리뷰 목록. first_row: 본문 fallback용 단일 row.
        data_rows = state.get("data") or []
        if isinstance(data_rows, dict):
            data_rows = [data_rows]
        first_row = data_rows[0] if data_rows else {}

        post_text = str(state.get("post") or first_row.get("content") or "").strip()
        if not post_text:
            return {"is_pass": False, "reason": "게시글 본문이 비어 있습니다."}

        # banned token 검사
        found_banned_tokens = [
            token
            for token in rules["local"]["banned_tokens"]
            if token in post_text
        ]
        if found_banned_tokens:
            return {
                "is_pass": False,
                "reason": f"템플릿/placeholder 문구가 포함되어 있습니다: {', '.join(found_banned_tokens)}",
            }

        # 메타 안내문 검사
        for line in post_text.splitlines():
            line_text = str(line or "").strip()
            compact_line = re.sub(rules["regex"]["line_compact"], "", line_text)
            meta_hit_count = sum(
                1
                for marker in rules["local"]["meta_markers"]
                if marker in compact_line
            )
            if meta_hit_count >= rules["local"]["meta_min_hits"]:
                return {
                    "is_pass": False,
                    "reason": f"본문 외 메타 안내문이 포함되어 있습니다: {line_text[:80]}",
                }

        # 문구/상투어 로컬 검사
        local_quality_issue = _find_local_quality_issue(post_text, rules)
        if local_quality_issue:
            return {"is_pass": False, "reason": local_quality_issue}

        # 가시 텍스트 길이·문장 수 검사
        visible_text = re.sub(rules["regex"]["html"], " ", post_text)
        visible_text = re.sub(rules["regex"]["url"], " ", visible_text)
        visible_text = re.sub(rules["regex"]["space"], " ", visible_text).strip()
        sentence_parts = [
            s.strip()
            for s in re.split(rules["regex"]["sentence_split"], visible_text)
            if s and len(s.strip()) >= rules["local"]["min_sentence_chars"]
        ]
        if (
            len(visible_text) < rules["local"]["min_visible_chars"]
            or len(sentence_parts) < rules["local"]["min_sentence_count"]
        ):
            logger.warning(
                f"local evaluation short text | chars={len(visible_text)} | "
                f"sentences={len(sentence_parts)} | preview={visible_text[:160]}"
            )
            return {
                "is_pass": False,
                "reason": (
                    "본문 텍스트가 부족합니다. 이미지/링크를 제외하고 "
                    f"{len(visible_text)}자, {len(sentence_parts)}문장입니다."
                ),
            }

        # LLM 평가
        sources_block = _build_sources_block(data_rows, rules)
        prompt = ChatPromptTemplate.from_template(EVALUATION_PROMPT_TEMPLATE)
        response = get_evaluation_llm().invoke(
            prompt.format(post=post_text, sources=sources_block)
        )
        return _parse_llm_evaluation_response(response)

    except Exception as e:
        data = state.get("data") or [{}]
        if isinstance(data, dict):
            data = [data]
        logger.error(f"evaluate_post_completion | Error={e} | time={time.time()} | crawling_id={data[0].get('crawling_id')}")
        return {"is_pass": False, "reason": str(e)}
