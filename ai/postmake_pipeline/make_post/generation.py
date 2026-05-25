import ast
import csv
import hashlib
import random
import re
import time
from functools import lru_cache
from html import escape
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from common.llm_factory import get_post_generation_llm
from common.logging_config import set_logging
from common.text_utils import parse_keywords
from get_data.get_data import get_image
from make_post.prompt import (
    CASUAL_SUB_PROMPTS,
    FORMAL_SUB_PROMPTS,
    LINE_COMPACT_PATTERN,
    MASTER_TEMPLATE,
    META_MARKERS,
    REGENERATE_REASON_SUB_PROMPT,
    REVIEW_TITLE_PREFIX,
    SENTENCE_STRUCTURE_PROMPTS,
    SOURCE_FACTS_TEMPLATE,
    TITLE_TEMPLATE,
    WRITING_ANGLE_PROMPTS,
)

logger = set_logging()

RESERVED_URL_HOSTS = {"example.com", "www.example.com", "example.org", "www.example.org", "example.net", "www.example.net"}
RESERVED_URL_SUFFIXES = (".example.com", ".example.org", ".example.net", ".example", ".test", ".invalid", ".localhost")
HTTP_URL_PATTERN = re.compile(r"https?://[^\s<>\")\]]+")
MAX_REGENERATION_COUNT = 1
LLM_RATE_LIMIT_RETRY_COUNT = 3
LLM_RATE_LIMIT_DEFAULT_WAIT_SECONDS = 12.0
LLM_RATE_LIMIT_BUFFER_SECONDS = 1.0

REFERENCE_EXAMPLE_CSV_PATH = Path(__file__).resolve().parents[1] / "temp" / "output_file.csv"


# ──────────────────────────────────────────────
# 상태 접근 헬퍼
# ──────────────────────────────────────────────

def _first_row(state: dict) -> dict:
    rows = state.get("data") or []
    return rows[0] if rows and isinstance(rows[0], dict) else {}


def _shop_id(state: dict):
    return _first_row(state).get("shop_id")


def _crawling_id(state: dict):
    return _first_row(state).get("crawling_id")


def _prompt_seed_id(sample_data: Optional[dict | list[dict]]) -> str:
    rows = sample_data if isinstance(sample_data, list) else [sample_data]
    crawling_ids = [
        row.get("crawling_id")
        for row in rows
        if isinstance(row, dict) and row.get("crawling_id") is not None
    ]
    if crawling_ids:
        return str(min(crawling_ids))
    return "unknown"


def _stable_prompt_index(seed_id: str, section: str, length: int) -> int | None:
    if length <= 0:
        return None
    seed = f"{seed_id}:{section}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % length


# ──────────────────────────────────────────────
# 리뷰 샘플링
# ──────────────────────────────────────────────

def _selected_keyword_sets(state: dict) -> tuple[set[str], set[str]]:
    selected_keywords = {
        str(keyword).strip()
        for keyword in state.get("keyword") or []
        if str(keyword).strip()
    }
    target_keywords = set()

    for keyword_stat in state.get("keyword_stats") or []:
        if not isinstance(keyword_stat, dict):
            continue

        keyword = str(keyword_stat.get("keyword") or "").strip()
        if keyword:
            selected_keywords.add(keyword)
            if keyword_stat.get("has_target_keyword"):
                target_keywords.add(keyword)

        for grouped_keyword in keyword_stat.get("keywords") or []:
            grouped_keyword = str(grouped_keyword).strip()
            if grouped_keyword:
                selected_keywords.add(grouped_keyword)
                if keyword_stat.get("has_target_keyword"):
                    target_keywords.add(grouped_keyword)

    return selected_keywords, target_keywords


def _score_review_rows(state: dict) -> list[tuple]:
    """선정 키워드와 많이 겹치는 긍정 리뷰를 우선 뽑기 위한 점수를 계산한다."""
    selected_keywords, target_keywords = _selected_keyword_sets(state)
    rows = [row for row in state.get("data") or [] if isinstance(row, dict)]
    candidates = [row for row in rows if row.get("sentimental") == "positive"] or rows
    scored_rows = []
    seen_ids = set()

    for index, row in enumerate(candidates):
        row_id = row.get("crawling_id") or index
        if row_id in seen_ids:
            continue
        seen_ids.add(row_id)

        content = str(row.get("content") or "").strip()
        if not content:
            continue

        row_keywords = parse_keywords(row)
        overlap_score = 0
        for row_keyword in row_keywords:
            for selected_keyword in selected_keywords:
                if row_keyword == selected_keyword:
                    overlap_score += 3
                elif row_keyword in selected_keyword or selected_keyword in row_keyword:
                    overlap_score += 1

        target_keyword_count = 0
        for row_keyword in row_keywords:
            if any(
                row_keyword == target_keyword
                or row_keyword in target_keyword
                or target_keyword in row_keyword
                for target_keyword in target_keywords
            ):
                target_keyword_count += 1

        try:
            row_score = float(row.get("score") or 0)
        except (TypeError, ValueError):
            row_score = 0.0

        content_bonus = min(len(content), 300) / 300
        total_score = (
            overlap_score * 10
            + target_keyword_count * 4
            + (2 if row.get("sentimental") == "positive" else 0)
            + row_score
            + content_bonus
        )
        scored_rows.append((total_score, overlap_score, target_keyword_count, row_score, -index, row))

    return sorted(scored_rows, reverse=True, key=lambda item: item[:-1])


def _select_sample_data(state: dict, sample_count: int = 5) -> list[dict]:
    """프롬프트에 넣을 대표 리뷰를 선정한다."""
    scored_rows = _score_review_rows(state)
    review_pool = scored_rows[:max(8, sample_count * 2)]
    sample_data = []
    selected_row_ids = set()

    if review_pool:
        first_row = review_pool[0][-1]
        sample_data.append(first_row)
        selected_row_ids.add(first_row.get("crawling_id") or id(first_row))

    while len(sample_data) < sample_count:
        choices = [
            item for item in review_pool
            if (item[-1].get("crawling_id") or id(item[-1])) not in selected_row_ids
        ]
        if not choices:
            break

        weights = []
        for total_score, overlap_score, target_keyword_count, _, _, _ in choices:
            weight = max(float(total_score or 0), 0.01)
            if not target_keyword_count:
                weight *= 0.65
            if not overlap_score:
                weight *= 0.7
            weights.append(weight)

        picked = random.choices(choices, weights=weights, k=1)[0][-1]
        sample_data.append(picked)
        selected_row_ids.add(picked.get("crawling_id") or id(picked))

    if not sample_data and state.get("data"):
        sample_data = [random.choice(state["data"])]

    return sample_data


def _select_article_url(state: dict, sample_data: list[dict] | dict | None) -> str | None:
    """샘플 리뷰와 원본 데이터에서 사용할 article_url을 고른다."""
    url_candidates = []
    if sample_data:
        if isinstance(sample_data, list):
            url_candidates.extend(row.get("article_url") for row in sample_data if isinstance(row, dict))
        elif isinstance(sample_data, dict):
            url_candidates.append(sample_data.get("article_url"))
    if state.get("data"):
        url_candidates.append(state["data"][0].get("article_url"))

    for candidate_url in url_candidates:
        candidate_url = str(candidate_url or "").strip()
        if candidate_url:
            return candidate_url
    return None


# ──────────────────────────────────────────────
# 프롬프트 포매팅 헬퍼
# ──────────────────────────────────────────────

def _clip_text(value: Optional[str], limit: int = 700) -> str:
    return str(value or "").strip()[:limit]


def _extract_image_urls(image_list: Optional[list]) -> list[str]:
    """이미지 row/list에서 실제 URL 문자열만 추출한다."""
    image_urls = []
    for image in image_list or []:
        image_url = None
        if isinstance(image, dict):
            image_url = image.get("image_url") or image.get("url")
        elif image is not None:
            image_url = str(image)

        image_url = str(image_url or "").strip()
        if image_url:
            image_urls.append(image_url)
    return image_urls


def _format_sample_data(sample_data: Optional[dict | list[dict]]) -> str:
    """샘플 리뷰를 프롬프트용 텍스트 블록으로 변환한다."""
    if not sample_data:
        return ""

    if isinstance(sample_data, list):
        lines = []
        for idx, review in enumerate(sample_data[:5], start=1):
            if not isinstance(review, dict):
                continue
            fields = [
                ("title", review.get("title")),
                ("content", _clip_text(review.get("content"), 280)),
                ("keywords", review.get("keywords")),
                ("sentimental", review.get("sentimental")),
                ("score", review.get("score")),
            ]
            body = "\n".join(
                f"  - {key}: {value}"
                for key, value in fields
                if value not in (None, "")
            )
            if body:
                lines.append(f"[{idx}]\n{body}")
        return "\n".join(lines)

    fields = [
        ("shop_id", sample_data.get("shop_id")),
        ("title", sample_data.get("title")),
        ("content", _clip_text(sample_data.get("content"), 280)),
        ("keywords", sample_data.get("keywords")),
        ("sentimental", sample_data.get("sentimental")),
        ("score", sample_data.get("score")),
    ]
    return "\n".join(f"- {key}: {value}" for key, value in fields if value not in (None, ""))


def _format_keyword_stats(keyword_stats: Optional[list[dict]]) -> str:
    if not keyword_stats:
        return ""
    lines = []
    for data in keyword_stats[:10]:
        lines.append(
            "- {keyword} | batch_count={batch_count} | average_score={average_score} | final_weight={final_weight}".format(
                keyword=data.get("keyword"),
                batch_count=data.get("batch_count"),
                average_score=data.get("average_score"),
                final_weight=data.get("final_weight"),
            )
        )
    return "\n".join(lines)


def _format_negative_keywords(negative_keywords: Optional[list[str]]) -> str:
    if not negative_keywords:
        return ""
    return ", ".join(negative_keywords[:5])


@lru_cache(maxsize=1)
def _load_reference_example_pool(
    csv_path: str = str(REFERENCE_EXAMPLE_CSV_PATH),
    pool_size: int = 200,
) -> tuple[tuple[str, str], ...]:
    """CSV에서 참고 예시 풀을 로드한다. reservoir sampling으로 pool_size개를 유지한다."""
    if not Path(csv_path).exists():
        return ()

    pool: list[tuple[str, str]] = []
    seen_count = 0
    try:
        with Path(csv_path).open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            for row in reader:
                review = str(row.get("Review") or row.get("review") or "").strip()
                if not review:
                    continue
                rating = str(row.get("Rating") or row.get("rating") or "").strip()
                seen_count += 1
                item = (rating, review)
                if len(pool) < pool_size:
                    pool.append(item)
                    continue
                replace_index = random.randint(0, seen_count - 1)
                if replace_index < pool_size:
                    pool[replace_index] = item
    except Exception as e:
        logger.error(f"_load_reference_example_pool | Error={e} | csv_path={csv_path}")
        return ()
    return tuple(pool)


def _format_reference_examples(row_count: int = 3) -> str:
    pool = list(_load_reference_example_pool())
    if not pool:
        return ""

    examples = random.sample(pool, k=min(row_count, len(pool)))
    lines = []
    for idx, (rating, review) in enumerate(examples, start=1):
        rating_line = f"  - rating: {rating}" if rating else ""
        review_line = f"  - review: {_clip_text(review, 180)}"
        body = "\n".join(line for line in (rating_line, review_line) if line)
        lines.append(f"[{idx}]\n{body}")
    return "\n".join(lines)


# ──────────────────────────────────────────────
# 프롬프트 빌더
# ──────────────────────────────────────────────

def _build_master_section(
    image_list: Optional[list],
    url: Optional[str],
    sample_data: Optional[dict | list[dict]],
) -> str:
    shop_sample = sample_data[0] if isinstance(sample_data, list) and sample_data else sample_data
    shop_title = str((shop_sample or {}).get("title", "") or "").strip()
    if shop_title.lower().startswith(REVIEW_TITLE_PREFIX):
        shop_title = shop_title.split("-", 1)[1].strip()

    image_html_lines = []
    for image_url in _extract_image_urls(image_list)[:1]:
        if image_url.lower().startswith("<img"):
            image_html_lines.append(image_url)
        else:
            image_html_lines.append(f'<img src="{escape(image_url, quote=True)}" alt="">')

    return MASTER_TEMPLATE.format(
        image_list="\n".join(image_html_lines),
        url=url or "",
        title=shop_title,
    )


def _build_common_post_prompt_sections(
    keyword: Optional[list[str]],
    image_list: Optional[list],
    url: Optional[str],
    sample_data: Optional[dict | list[dict]],
    keyword_stats: Optional[list[dict]],
    negative_keywords: Optional[list[str]],
) -> list[str]:
    """초안 생성과 재생성 프롬프트가 공유하는 앞부분 섹션을 만든다."""
    seed_id = _prompt_seed_id(sample_data)
    writing_angle_index = _stable_prompt_index(seed_id, "writing_angle", len(WRITING_ANGLE_PROMPTS))
    sentence_structure_index = _stable_prompt_index(
        seed_id,
        "sentence_structure",
        len(SENTENCE_STRUCTURE_PROMPTS),
    )
    writing_angle_prompt = WRITING_ANGLE_PROMPTS[writing_angle_index] if writing_angle_index is not None else ""
    sentence_structure_prompt = (
        SENTENCE_STRUCTURE_PROMPTS[sentence_structure_index]
        if sentence_structure_index is not None
        else ""
    )
    writing_angle_label = writing_angle_prompt.splitlines()[0][:80] if writing_angle_prompt else ""
    sentence_structure_label = sentence_structure_prompt.splitlines()[0][:80] if sentence_structure_prompt else ""
    logger.info(
        f"prompt variant selected | seed_id={seed_id} | "
        f"writing_angle={writing_angle_index}:{writing_angle_label} | "
        f"sentence_structure={sentence_structure_index}:{sentence_structure_label}"
    )

    return [
        _build_master_section(image_list, url, sample_data),
        "# [KEYWORDS]",
        ", ".join(keyword or []),
        "# [KEYWORD PRIORITY]",
        _format_keyword_stats(keyword_stats),
        "# [KEYWORD PRIORITY RULE]",
        "final_weight가 높은 키워드를 우선 반영하되, 숫자나 점수 자체를 본문에 쓰지 마세요.\n"
        "메뉴명이나 대상어가 붙은 키워드는 해당 메뉴/대상에 대한 평가로만 사용하고, 일반 맛 평가처럼 섞어 쓰지 마세요.",
        "# [AVOID KEYWORDS]",
        _format_negative_keywords(negative_keywords),
        "# [AVOID KEYWORD RULE]",
        "AVOID KEYWORDS에 있는 요소는 장점처럼 강조하지 말고, 가능한 한 언급하지 마세요.",
        "# [WRITING ANGLE]",
        writing_angle_prompt,
        "# [SENTENCE STRUCTURE]",
        sentence_structure_prompt,
        "# [REFERENCE WRITING EXAMPLES]",
        _format_reference_examples(),
        "# [REFERENCE EXAMPLE RULE]",
        "REFERENCE WRITING EXAMPLES는 문장 밀도와 구체성 참고용입니다.\n"
        "예시의 메뉴명, 장소명, 사실관계는 절대 가져오지 말고 SOURCE FACTS와 TOP SOURCE REVIEWS에 있는 사실만 사용하세요.",
        "# [TOP SOURCE REVIEWS]",
        _format_sample_data(sample_data),
    ]


def _source_facts_sections(source_facts: Optional[str]) -> list[str]:
    return [
        "# [SOURCE FACTS]",
        str(source_facts or "").strip(),
    ]


def _pass_check_sections(rule_text: str) -> list[str]:
    return [
        "# [PASS CHECK BEFORE OUTPUT]",
        rule_text,
    ]


def _build_generation_prompt(
    keyword: list[str],
    image_list: Optional[list] = None,
    url: Optional[str] = None,
    sample_data: Optional[dict | list[dict]] = None,
    keyword_stats: Optional[list[dict]] = None,
    negative_keywords: Optional[list[str]] = None,
    source_facts: Optional[str] = None,
) -> str:
    """게시글 초안 생성 프롬프트를 조립한다."""
    try:
        mode_prompts = CASUAL_SUB_PROMPTS + FORMAL_SUB_PROMPTS
        seed_id = _prompt_seed_id(sample_data)
        mode_index = _stable_prompt_index(seed_id, "mode", len(mode_prompts))
        mode_prompt = mode_prompts[mode_index] if mode_index is not None else ""
        mode_label = ""
        for line in mode_prompt.splitlines():
            line = line.strip()
            if line.startswith("# [MODE:"):
                mode_label = line.replace("# [MODE:", "").replace("]", "").strip()
                break
        logger.info(f"prompt variant selected | seed_id={seed_id} | mode={mode_index}:{mode_label}")

        return "\n".join([
            *_build_common_post_prompt_sections(
                keyword,
                image_list,
                url,
                sample_data,
                keyword_stats,
                negative_keywords,
            ),
            "# [SOURCE REVIEW RULE]",
            "TOP SOURCE REVIEWS는 선정 키워드와 많이 겹치고 메뉴명/대상어가 있는 리뷰를 우선 고른 근거입니다.\n"
            "여러 리뷰에서 반복되는 구체적인 관찰 포인트를 반영하되, 원문을 그대로 복사하지 마세요.",
            *_source_facts_sections(source_facts),
            "# [SOURCE FACT RULE]",
            "본문은 SOURCE FACTS의 사실만 조합해서 작성하세요.\n"
            "SOURCE FACTS가 부족하면 TOP SOURCE REVIEWS에서 직접 확인되는 표현만 보완하고, 추측으로 메뉴명/재료명/장소명을 만들지 마세요.\n"
            "SOURCE FACTS를 모두 나열하지 말고 메뉴/맛·식감·양/서비스·분위기·가격·상황 중 서로 다른 축 3개 안팎을 골라 조합하세요.",
            *_pass_check_sections(
                "출력 전 스스로 확인하세요. 본문 텍스트가 이미지/링크를 제외하고 4문장 이상, 230자 이상이어야 합니다.\n"
                "SOURCE FACTS 또는 TOP SOURCE REVIEWS에서 확인되는 구체 대상어+평가를 최소 2개 넣어야 합니다.\n"
                "가격, 메뉴 구성, 무한리필, 주차, 웨이팅 같은 정보는 근거에 정확히 있을 때만 씁니다."
            ),
            mode_prompt,
        ])
    except Exception as e:
        sample_for_log = sample_data[0] if isinstance(sample_data, list) and sample_data else sample_data
        crawling_id = (sample_for_log or {}).get("crawling_id")
        logger.error(f"_build_generation_prompt | Error={e} | crawling_id={crawling_id}")
        return ""


def _build_regenerate_prompt(
    reason: str,
    keyword: Optional[list[str]] = None,
    image_list: Optional[list] = None,
    url: Optional[str] = None,
    sample_data: Optional[dict | list[dict]] = None,
    keyword_stats: Optional[list[dict]] = None,
    negative_keywords: Optional[list[str]] = None,
    source_facts: Optional[str] = None,
    previous_post: Optional[str] = None,
) -> str:
    """평가 실패 사유를 반영한 재생성 프롬프트를 조립한다."""
    try:
        mode_prompts = CASUAL_SUB_PROMPTS + FORMAL_SUB_PROMPTS
        seed_id = _prompt_seed_id(sample_data)
        mode_index = _stable_prompt_index(seed_id, "mode", len(mode_prompts))
        mode_prompt = mode_prompts[mode_index] if mode_index is not None else ""
        mode_label = ""
        for line in mode_prompt.splitlines():
            line = line.strip()
            if line.startswith("# [MODE:"):
                mode_label = line.replace("# [MODE:", "").replace("]", "").strip()
                break
        logger.info(f"prompt variant selected | seed_id={seed_id} | mode={mode_index}:{mode_label}")

        return "\n".join([
            *_build_common_post_prompt_sections(
                keyword,
                image_list,
                url,
                sample_data,
                keyword_stats,
                negative_keywords,
            ),
            *_source_facts_sections(source_facts),
            "# [PREVIOUS POST]",
            str(previous_post or "").strip(),
            REGENERATE_REASON_SUB_PROMPT.format(reason=reason),
            "# [REGENERATION RULE]",
            "PREVIOUS POST를 그대로 고치지 말고, 실패 사유가 된 표현을 제거한 뒤 SOURCE FACTS에 있는 사실만 사용해서 새로 작성하세요.\n"
            "구체적인 대상+평가를 최소 2개 이상 포함하고, 상투적인 칭찬만 반복하지 마세요.\n"
            "PREVIOUS POST와 다른 관점/문장 순서로 쓰고, SOURCE FACTS 중 서로 다른 축의 사실을 골라 조합하세요.",
            *_pass_check_sections(
                "출력 전 스스로 확인하세요. 본문 텍스트가 이미지/링크를 제외하고 4문장 이상, 230자 이상이어야 합니다.\n"
                "평가 실패 사유에 나온 문제를 반복하지 말고, 근거 없는 가격/메뉴/시설 정보는 모두 빼세요."
            ),
            mode_prompt,
        ])
    except Exception as e:
        sample_for_log = sample_data[0] if isinstance(sample_data, list) and sample_data else sample_data
        crawling_id = (sample_for_log or {}).get("crawling_id")
        logger.error(f"_build_regenerate_prompt | Error={e} | crawling_id={crawling_id}")
        return ""


# ──────────────────────────────────────────────
# LLM 응답 후처리
# ──────────────────────────────────────────────

def _is_rate_limit_error(error: Exception) -> bool:
    error_text = str(error).lower()
    return (
        "rate_limit" in error_text
        or "rate limit" in error_text
        or "429" in error_text
        or "too many requests" in error_text
    )


def _rate_limit_wait_seconds(error: Exception) -> float:
    retry_match = re.search(r"try again in\s+([0-9.]+)s", str(error), flags=re.IGNORECASE)
    if retry_match:
        return max(float(retry_match.group(1)) + LLM_RATE_LIMIT_BUFFER_SECONDS, 1.0)
    return LLM_RATE_LIMIT_DEFAULT_WAIT_SECONDS


def _invoke_with_retry(llm, prompt: str, node_name: str, state: dict):
    """LLM rate limit이면 잠깐 기다렸다가 재시도한다."""
    for attempt in range(LLM_RATE_LIMIT_RETRY_COUNT):
        try:
            return llm.invoke(prompt)
        except Exception as e:
            if not _is_rate_limit_error(e) or attempt + 1 >= LLM_RATE_LIMIT_RETRY_COUNT:
                raise

            wait_seconds = _rate_limit_wait_seconds(e)
            logger.warning(
                f"llm rate limit | node={node_name} | shop_id={_shop_id(state)} | "
                f"attempt={attempt + 1}/{LLM_RATE_LIMIT_RETRY_COUNT} | "
                f"wait_seconds={wait_seconds:.1f} | error={str(e)[:300]}"
            )
            time.sleep(wait_seconds)


def _response_text(response) -> str:
    content = response.content if hasattr(response, "content") else str(response)
    return str(content or "").strip()


def _unwrap_content_assignment(post: str) -> str:
    for _ in range(2):
        content_match = re.match(
            r"^content=(?P<quoted>'(?:\\.|[^'])*'|\"(?:\\.|[^\"])*\")(?:\s+\w+=.*)?$",
            post,
            flags=re.DOTALL,
        )
        if not content_match:
            break
        try:
            post = ast.literal_eval(content_match.group("quoted"))
        except (SyntaxError, ValueError):
            post = content_match.group("quoted")[1:-1]
        post = str(post or "").strip()
    return post


def _remove_think_block(post: str) -> str:
    post = re.sub(r"(?is)<think\b[^>]*>.*?</think\s*>", "", post).strip()
    think_index = post.lower().find("<think")
    if think_index == -1:
        return post

    after_think = post[think_index:]
    html_start = re.search(
        r"(?is)<(?:p|div|section|article|h[1-6]|ul|ol|li|blockquote|strong|br|img|a)\b",
        after_think,
    )
    if html_start:
        return (post[:think_index] + after_think[html_start.start():]).strip()

    split_post = re.split(r"\n\s*\n", after_think, maxsplit=1)
    return (post[:think_index] + split_post[-1]).strip() if len(split_post) > 1 else post[:think_index].strip()


def _remove_code_fence(post: str) -> str:
    fence_match = re.search(r"(?is)```(?:html|markdown|text)?\s*(?P<body>.*?)\s*```", post)
    if fence_match:
        return fence_match.group("body").strip()

    post = re.sub(r"(?im)^\s*```(?:html|markdown|text)?\s*$", "", post).strip()
    return re.sub(r"(?im)^\s*```\s*$", "", post).strip()


def _remove_intro_labels(post: str) -> str:
    for _ in range(3):
        normalized_post = re.sub(
            r"(?is)^\s*(?:assistant|ai|answer|final|답변|본문|게시글|출력)\s*[:：]\s*",
            "",
            post,
        ).strip()
        normalized_post = re.sub(
            r"(?is)^\s*(?:여기 있습니다|작성했습니다|완성했습니다|아래와 같습니다)\s*[:：]?\s*",
            "",
            normalized_post,
        ).strip()
        if normalized_post == post:
            break
        post = normalized_post
    return post


def _allowed_url(value: str) -> bool:
    text = str(value or "").strip()
    if not text or any(char.isspace() for char in text):
        return False

    parsed = urlparse(text if "://" in text else f"https://{text}")
    hostname = (parsed.hostname or "").lower().rstrip(".")
    return (
        parsed.scheme.lower() in {"http", "https"}
        and bool(hostname)
        and hostname not in RESERVED_URL_HOSTS
        and not any(hostname.endswith(suffix) for suffix in RESERVED_URL_SUFFIXES)
    )


def _remove_reserved_urls(post: str) -> str:
    return HTTP_URL_PATTERN.sub(
        lambda match: match.group(0) if _allowed_url(match.group(0)) else "",
        str(post or ""),
    ).strip()


def _remove_meta_lines(post: str) -> str:
    cleaned_lines = []
    for line in post.splitlines():
        line_text = str(line or "").strip()
        compact_line = re.sub(LINE_COMPACT_PATTERN, "", line_text)
        meta_hit_count = sum(1 for marker in META_MARKERS if marker in compact_line)
        if meta_hit_count >= 2:
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip()


def _clean_generated_post(response) -> str:
    """LLM 응답에서 본문 외 래퍼/메타 문구를 제거한다."""
    post = _response_text(response)
    post = _unwrap_content_assignment(post)
    post = _remove_think_block(post)
    post = _remove_code_fence(post)
    post = _remove_intro_labels(post)
    post = _remove_reserved_urls(post)
    return _remove_meta_lines(post)


def _append_required_outputs(post: str, image_list: list, url: str | None) -> str:
    """생성 결과에 필수 이미지/링크 출력이 빠졌으면 보강한다."""
    image_urls = _extract_image_urls(image_list)
    if image_urls and not any(image_url in post for image_url in image_urls):
        image_url = image_urls[0]
        image_html = (
            image_url
            if image_url.lower().startswith("<img")
            else f'<img src="{escape(image_url, quote=True)}" alt="">'
        )
        post = f"{post}\n\n{image_html}"

    link_html = str(url or "").strip()
    if link_html and link_html not in post:
        post = f"{post}\n\n{link_html}"

    return post


# ──────────────────────────────────────────────
# 생성 컨텍스트
# ──────────────────────────────────────────────

def _build_generation_context(state: dict) -> dict:
    sample_data = state.get("sample_data") or _select_sample_data(state)
    # image_list는 state에 캐싱된 값을 우선 사용해 regenerate 시 DB 재조회를 막는다.
    image_list = state.get("image_list")
    if image_list is None:
        image_list = get_image(state.get("data") or [])
    return {
        "image_list": image_list,
        "sample_data": sample_data,
        "url": _select_article_url(state, sample_data),
    }


def _extract_source_facts(llm, state: dict, sample_data: list[dict]) -> str:
    """대표 리뷰에서 게시글에 사용할 수 있는 근거 사실을 추출한다."""
    try:
        facts_prompt = SOURCE_FACTS_TEMPLATE.format(
            action_text="작성을",
            usage_text="게시글에",
            keywords=", ".join(state.get("keyword") or []),
            reviews=_format_sample_data(sample_data),
        )
        response = _invoke_with_retry(llm, facts_prompt, "make_post.source_facts", state)
        return _response_text(response)
    except Exception as e:
        logger.error(f"source facts extraction error | Error={e} | shop_id={_shop_id(state)}")
        return ""


# ──────────────────────────────────────────────
# LangGraph 노드
# ──────────────────────────────────────────────

def make_post(state: dict) -> dict:
    """키워드, 이미지, 샘플 analysis row를 기반으로 게시글 초안을 만든다."""
    try:
        logger.info(f"make_post start | shop_id={_shop_id(state)}")
        llm = get_post_generation_llm()
        context = _build_generation_context(state)
        source_facts = _extract_source_facts(llm, state, context["sample_data"])

        prompt = _build_generation_prompt(
            state["keyword"],
            context["image_list"],
            context["url"],
            context["sample_data"],
            state.get("keyword_stats"),
            state.get("negative_keywords"),
            source_facts,
        )
        response = _invoke_with_retry(llm, prompt, "make_post.body", state)
        post = _clean_generated_post(response)
        post = _append_required_outputs(post, context["image_list"], context["url"])

        logger.info(f"make_post end | shop_id={_shop_id(state)} | post_len={len(post)}")
        return {
            **state,
            "post": post,
            "sample_data": context["sample_data"],
            "image_list": context["image_list"],
            "source_facts": source_facts,
        }
    except Exception as e:
        logger.error(f"make_post failed | Error={e} | time={time.time()} | crawling_id={_crawling_id(state)}")
        return {
            **state,
            "retry_count": state.get("retry_count", 0) + 1,
        }


def make_title(state: dict) -> dict:
    """생성된 게시글 본문을 바탕으로 제목을 만든다."""
    try:
        logger.info(f"make_title start | shop_id={_shop_id(state)}")
        llm = get_post_generation_llm()
        prompt = TITLE_TEMPLATE.format(data=state["post"])
        response = _invoke_with_retry(llm, prompt, "make_title", state)
        title = _response_text(response)

        logger.info(f"make_title end | shop_id={_shop_id(state)} | title_len={len(title)}")
        return {
            **state,
            "title": title,
        }
    except Exception as e:
        logger.error(f"make_title failed | Error={e} | time={time.time()} | crawling_id={_crawling_id(state)}")
        return state


def regenerate_post(state: dict) -> dict:
    """평가 실패 사유를 반영해 게시글을 다시 생성한다."""
    try:
        retry_count = state.get("retry_count", 0)
        if retry_count >= MAX_REGENERATION_COUNT:
            return state

        logger.info(f"regenerate_post start | shop_id={_shop_id(state)} | retry_count={retry_count}")
        llm = get_post_generation_llm()
        context = _build_generation_context(state)
        source_facts = str(state.get("source_facts") or "").strip()

        if state.get("reason"):
            prompt = _build_regenerate_prompt(
                state["reason"],
                state["keyword"],
                context["image_list"],
                context["url"],
                context["sample_data"],
                state.get("keyword_stats"),
                state.get("negative_keywords"),
                source_facts,
                state.get("post"),
            )
        else:
            prompt = _build_generation_prompt(
                state["keyword"],
                context["image_list"],
                context["url"],
                context["sample_data"],
                state.get("keyword_stats"),
                state.get("negative_keywords"),
                source_facts,
            )

        response = _invoke_with_retry(llm, prompt, "regenerate_post.body", state)
        post = _clean_generated_post(response)
        post = _append_required_outputs(post, context["image_list"], context["url"])

        logger.info(
            f"regenerate_post end | shop_id={_shop_id(state)} | "
            f"retry_count={retry_count + 1} | post_len={len(post)}"
        )
        return {
            **state,
            "post": post,
            "sample_data": context["sample_data"],
            "source_facts": source_facts,
            "reason": None,
            "is_pass": None,
            "retry_count": retry_count + 1,
        }
    except Exception as e:
        logger.error(
            f"regenerate_post failed | retry_count={state.get('retry_count', 0)} | "
            f"reason={state.get('reason')} | Error={e} | time={time.time()} | crawling_id={_crawling_id(state)}"
        )
        return {
            **state,
            "retry_count": state.get("retry_count", 0) + 1,
        }
