from langgraph.graph import StateGraph, START, END
from typing import Optional, TypedDict
from common.logging_config import set_logging
from common.connection import PGVectorStore
from make_post.evaluation import evaluate_post_completion
from common.llm_factory import get_llm
from get_data.get_another import get_similar_post
from common.prompt import Create_Prompt
from get_data.get_another import get_image
import time
import random
import re
from urllib.parse import urlparse

logger = set_logging()

INITIAL_SIMILARITY_DISTANCE_THRESHOLD = 0.18
REGENERATED_SIMILARITY_DISTANCE_THRESHOLD = 0.12
RESERVED_URL_HOSTS = {"example.com", "www.example.com", "example.org", "www.example.org", "example.net", "www.example.net"}
RESERVED_URL_SUFFIXES = (".example.com", ".example.org", ".example.net", ".example", ".test", ".invalid", ".localhost")
HTTP_URL_PATTERN = re.compile(r"https?://[^\s<>\")\]]+")


"""===================================================================="""


class State(TypedDict):
    """LangGraph 노드들이 공유하는 게시글 생성 상태."""
    keyword: list[str]
    keyword_stats: Optional[list[dict]]
    negative_keywords: Optional[list[str]]
    data: list[dict]
    post: Optional[str]
    title: Optional[str]
    similar_post: Optional[list[str]]
    reason: Optional[str]
    sample_data: Optional[dict | list[dict]]
    source_facts: Optional[str]
    is_pass: Optional[bool]
    retry_count: int


def make_post(state: State) -> State:
    """키워드, 이미지, 샘플 analysis row를 기반으로 게시글 초안을 만든다."""
    try:
        logger.info(f"make_post start | shop_id={state['data'][0].get('shop_id')}")
        llm = get_llm()
        image_list = get_image(state['data'])

        # 선정 키워드와 많이 겹치고 대상어+평가 키워드가 있는 리뷰를 우선 샘플로 보낸다.
        selected_keywords = {str(keyword).strip() for keyword in state.get('keyword') or [] if str(keyword).strip()}
        target_keywords = set()
        for keyword_stat in state.get('keyword_stats') or []:
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

        rows = [row for row in state.get('data') or [] if isinstance(row, dict)]
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

            keywords_value = row.get("keywords") or ""
            if isinstance(keywords_value, str):
                row_keywords = [kw.strip() for kw in keywords_value.split("#") if kw.strip()]
            elif isinstance(keywords_value, list):
                row_keywords = [str(kw).strip() for kw in keywords_value if str(kw).strip()]
            else:
                row_keywords = []
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

        scored_rows.sort(reverse=True, key=lambda item: item[:-1])
        sample_data = [row for *_, row in scored_rows[:5]]
        if not sample_data and state['data']:
            sample_data = [random.choice(state['data'])]
        url_candidates = []
        if sample_data:
            if isinstance(sample_data, list):
                url_candidates.extend(row.get('article_url') for row in sample_data if isinstance(row, dict))
            elif isinstance(sample_data, dict):
                url_candidates.append(sample_data.get('article_url'))
        if state.get('data'):
            url_candidates.append(state['data'][0].get('article_url'))
        url = None
        for candidate_url in url_candidates:
            candidate_url = str(candidate_url or "").strip()
            if candidate_url:
                url = candidate_url
                break
        source_review_block = Create_Prompt._format_sample_data(sample_data)
        source_facts = ""
        try:
            facts_prompt = f"""
# [SYSTEM ROLE]
당신은 식당 게시글 작성을 위한 근거 사실만 추리는 편집자입니다.
아래 TOP SOURCE REVIEWS와 KEYWORDS를 보고, 게시글에 사용 가능한 사실만 3~5개 뽑으세요.

# [KEYWORDS]
{", ".join(state.get('keyword') or [])}

# [TOP SOURCE REVIEWS]
{source_review_block}

# [RULES]
1. 리뷰에 직접 나오거나 자연스럽게 확인되는 사실만 쓰세요.
2. 리뷰에 메뉴명/음식명/대상어가 있으면 최소 2개 이상을 원문 표기 그대로 포함하세요.
3. 각 bullet은 반드시 "구체 대상어 + 평가/맥락" 형태로 쓰세요. 예: "김치뽀글이는 매콤하다는 평가가 있다."
4. "메인 메뉴", "반찬 구성", "음식", "요리", "메뉴" 같은 넓은 일반명사만으로 대상어를 대체하지 마세요.
5. "맛있다", "좋다", "만족스럽다" 같은 일반 칭찬만 있는 항목은 피하세요.
6. 없는 메뉴명, 재료명, 지명, 고유명사를 새로 만들지 마세요.
7. 출력은 bullet 3~5개만 작성하세요. 설명문은 쓰지 마세요.
"""
            facts_response = llm.invoke(facts_prompt)
            source_facts = str(facts_response)
            if hasattr(facts_response, "content"):
                source_facts = facts_response.content
            source_facts = source_facts.strip()
        except Exception as e:
            logger.error(f"source facts extraction error | Error={e} | shop_id={state['data'][0].get('shop_id')}")

        prompt = Create_Prompt.get_prompt(
            state['keyword'],
            image_list,
            url,
            sample_data,
            state.get('keyword_stats'),
            state.get('negative_keywords'),
            source_facts,
        )
        response = llm.invoke(prompt)
        post = str(response)
        if hasattr(response, "content"):
            post = response.content
        post = HTTP_URL_PATTERN.sub(
            lambda match: (
                match.group(0)
                if (
                    str(match.group(0) or "").strip()
                    and not any(char.isspace() for char in str(match.group(0) or "").strip())
                    and (
                        (
                            parsed := urlparse(
                                str(match.group(0)).strip()
                                if "://" in str(match.group(0)).strip()
                                else f"https://{str(match.group(0)).strip()}"
                            )
                        ).scheme.lower() in {"http", "https"}
                    )
                    and parsed.hostname
                    and parsed.hostname.lower().rstrip(".") not in RESERVED_URL_HOSTS
                    and not any(
                        parsed.hostname.lower().rstrip(".").endswith(suffix)
                        for suffix in RESERVED_URL_SUFFIXES
                    )
                )
                else ""
            ),
            str(post or ""),
        ).strip()
        image_urls = []
        for image in image_list or []:
            image_url = None
            if isinstance(image, dict):
                image_url = image.get('image_url') or image.get('url')
            elif image is not None:
                image_url = str(image)
            image_url = str(image_url or "").strip()
            if image_url:
                image_urls.append(image_url)
        if image_urls and not any(image_url in post for image_url in image_urls):
            post = f"{post}\n\n{image_urls[0]}"
        link_html = str(url or "").strip()
        if link_html and link_html not in post:
            post = f"{post}\n\n{link_html}"
        logger.info(f"make_post end | shop_id={state['data'][0].get('shop_id')} | post_len={len(post)}")
        
        return {
            **state,
            'post': post,
            'sample_data': sample_data,
            'source_facts': source_facts,
        }
    except Exception as e:
        logger.error(f"Error={e} | time={time.time()} | crawling_id={state['data'][0].get('crawling_id')}")
        return {
            **state,
            'retry_count': state.get('retry_count', 0) + 1,
        }

def make_title(state: State) -> State:
    """생성된 게시글 본문을 바탕으로 제목을 만든다."""
    try:
        logger.info(f"make_title start | shop_id={state['data'][0].get('shop_id')}")
        llm = get_llm()
        prompt = Create_Prompt.get_title_prompt(state['post'])
        response = llm.invoke(prompt)
        title = str(response)
        if hasattr(response, "content"):
            title = response.content
        logger.info(f"make_title end | shop_id={state['data'][0].get('shop_id')} | title_len={len(title)}")
        return {
            **state,
            'title': title,
        }
    except Exception as e:
        logger.error(f"Error={e} | time={time.time()} | crawling_id={state['data'][0].get('crawling_id')}")
        return state

def embedding(state: State, similarity_distance_threshold: float = INITIAL_SIMILARITY_DISTANCE_THRESHOLD) -> State:
    """생성 게시글과 기존 벡터 문서의 유사도를 조회한다."""
    try:
        logger.info(f"embedding start | shop_id={state['data'][0].get('shop_id')}")
        vectorstore = PGVectorStore().get_vectorstore()
        results = vectorstore.similarity_search_with_score(state['post'], k=5)
        retry_count = state.get('retry_count', 0)
        threshold = similarity_distance_threshold
        if retry_count > 0:
            threshold = REGENERATED_SIMILARITY_DISTANCE_THRESHOLD

        # PGVector cosine score는 distance라서 값이 낮을수록 기존 글과 더 유사하다.
        similar_results = [
            document
            for document, score in results
            if score <= threshold
        ]
        state['similar_post'] = None
        if similar_results and retry_count == 0:
            state['similar_post'] = get_similar_post(similar_results)
        best_score = min((score for _, score in results), default=None)
        top_scores = [round(score, 4) for _, score in results]
        logger.info(
            f"embedding end | shop_id={state['data'][0].get('shop_id')} | "
            f"similar_count={len(similar_results)} | "
            f"similar_prompt_count={len(state.get('similar_post') or [])} | "
            f"best_score={best_score} | threshold={threshold} | "
            f"retry_count={retry_count} | top_scores={top_scores}"
        )
        return state
    except Exception as e:
        logger.error(f"Error={e} | time={time.time()} | crawling_id={state['data'][0].get('crawling_id')}")
        return state

def regenerate_post(state: State) -> State:
    """평가 실패 사유 또는 유사 게시글을 반영해 게시글을 다시 생성한다."""
    try:
        retry_count = state.get('retry_count', 0)
        if retry_count >= 2:
            return state
        logger.info(f"regenerate_post start | shop_id={state['data'][0].get('shop_id')} | retry_count={retry_count}")
        llm = get_llm()
        image_list = get_image(state['data'])
        sample_data = state.get('sample_data')
        if not sample_data:
            selected_keywords = {str(keyword).strip() for keyword in state.get('keyword') or [] if str(keyword).strip()}
            target_keywords = set()
            for keyword_stat in state.get('keyword_stats') or []:
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

            rows = [row for row in state.get('data') or [] if isinstance(row, dict)]
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

                keywords_value = row.get("keywords") or ""
                if isinstance(keywords_value, str):
                    row_keywords = [kw.strip() for kw in keywords_value.split("#") if kw.strip()]
                elif isinstance(keywords_value, list):
                    row_keywords = [str(kw).strip() for kw in keywords_value if str(kw).strip()]
                else:
                    row_keywords = []
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

            scored_rows.sort(reverse=True, key=lambda item: item[:-1])
            sample_data = [row for *_, row in scored_rows[:5]]
            if not sample_data and state['data']:
                sample_data = [random.choice(state['data'])]
        url_candidates = []
        if sample_data:
            if isinstance(sample_data, list):
                url_candidates.extend(row.get('article_url') for row in sample_data if isinstance(row, dict))
            elif isinstance(sample_data, dict):
                url_candidates.append(sample_data.get('article_url'))
        if state.get('data'):
            url_candidates.append(state['data'][0].get('article_url'))
        url = None
        for candidate_url in url_candidates:
            candidate_url = str(candidate_url or "").strip()
            if candidate_url:
                url = candidate_url
                break
        source_facts = str(state.get('source_facts') or "").strip()
        if not source_facts:
            source_review_block = Create_Prompt._format_sample_data(sample_data)
            try:
                facts_prompt = f"""
# [SYSTEM ROLE]
당신은 식당 게시글 재작성을 위한 근거 사실만 추리는 편집자입니다.
아래 TOP SOURCE REVIEWS와 KEYWORDS를 보고, 재작성에 사용 가능한 사실만 3~5개 뽑으세요.

# [KEYWORDS]
{", ".join(state.get('keyword') or [])}

# [TOP SOURCE REVIEWS]
{source_review_block}

# [RULES]
1. 리뷰에 직접 나오거나 자연스럽게 확인되는 사실만 쓰세요.
2. 리뷰에 메뉴명/음식명/대상어가 있으면 최소 2개 이상을 원문 표기 그대로 포함하세요.
3. 각 bullet은 반드시 "구체 대상어 + 평가/맥락" 형태로 쓰세요. 예: "김치뽀글이는 매콤하다는 평가가 있다."
4. "메인 메뉴", "반찬 구성", "음식", "요리", "메뉴" 같은 넓은 일반명사만으로 대상어를 대체하지 마세요.
5. "맛있다", "좋다", "만족스럽다" 같은 일반 칭찬만 있는 항목은 피하세요.
6. 없는 메뉴명, 재료명, 지명, 고유명사를 새로 만들지 마세요.
7. 출력은 bullet 3~5개만 작성하세요. 설명문은 쓰지 마세요.
"""
                facts_response = llm.invoke(facts_prompt)
                source_facts = str(facts_response)
                if hasattr(facts_response, "content"):
                    source_facts = facts_response.content
                source_facts = source_facts.strip()
            except Exception as e:
                logger.error(f"source facts extraction error | Error={e} | shop_id={state['data'][0].get('shop_id')}")

        # 실패 사유가 있으면 품질 보정 프롬프트를, 유사 게시글이 있으면 중복 회피 프롬프트를 우선한다.
        prompt = Create_Prompt.get_prompt(
            state['keyword'],
            image_list,
            url,
            sample_data,
            state.get('keyword_stats'),
            state.get('negative_keywords'),
            source_facts,
        )
        if state['similar_post']:
            prompt = Create_Prompt.get_regenerate_prompt(
                state['similar_post'],
                state['keyword'],
                image_list,
                url,
                sample_data,
                state.get('keyword_stats'),
                state.get('negative_keywords'),
                source_facts,
            )
        if state['reason']:
            prompt = Create_Prompt.get_regenerate_reason_prompt(
                state['reason'],
                state['keyword'],
                image_list,
                url,
                sample_data,
                state.get('keyword_stats'),
                state.get('negative_keywords'),
                source_facts,
                state.get('post'),
            )
        response = llm.invoke(prompt)
        post = str(response)
        if hasattr(response, "content"):
            post = response.content
        post = HTTP_URL_PATTERN.sub(
            lambda match: (
                match.group(0)
                if (
                    str(match.group(0) or "").strip()
                    and not any(char.isspace() for char in str(match.group(0) or "").strip())
                    and (
                        (
                            parsed := urlparse(
                                str(match.group(0)).strip()
                                if "://" in str(match.group(0)).strip()
                                else f"https://{str(match.group(0)).strip()}"
                            )
                        ).scheme.lower() in {"http", "https"}
                    )
                    and parsed.hostname
                    and parsed.hostname.lower().rstrip(".") not in RESERVED_URL_HOSTS
                    and not any(
                        parsed.hostname.lower().rstrip(".").endswith(suffix)
                        for suffix in RESERVED_URL_SUFFIXES
                    )
                )
                else ""
            ),
            str(post or ""),
        ).strip()
        image_urls = []
        for image in image_list or []:
            image_url = None
            if isinstance(image, dict):
                image_url = image.get('image_url') or image.get('url')
            elif image is not None:
                image_url = str(image)
            image_url = str(image_url or "").strip()
            if image_url:
                image_urls.append(image_url)
        if image_urls and not any(image_url in post for image_url in image_urls):
            post = f"{post}\n\n{image_urls[0]}"
        link_html = str(url or "").strip()
        if link_html and link_html not in post:
            post = f"{post}\n\n{link_html}"
        logger.info(f"regenerate_post end | shop_id={state['data'][0].get('shop_id')} | retry_count={retry_count + 1} | post_len={len(post)}")
        return {
            **state,
            'post': post,
            'sample_data': sample_data,
            'source_facts': source_facts,
            'similar_post': None,
            'reason': None,
            'is_pass': None,
            'retry_count': retry_count + 1,
        }
    except Exception as e:
        logger.error(f"Error={e} | time={time.time()} | crawling_id={state['data'][0].get('crawling_id')}")
        return {
            **state,
            'retry_count': state.get('retry_count', 0) + 1,
        }

def evaluate_post(state: State) -> State:
    """완성된 게시글이 저장 가능한 품질인지 검사한다."""
    try:
        logger.info(f"evaluate_post start | shop_id={state['data'][0].get('shop_id')}")
        result = evaluate_post_completion(state)
        logger.info(f"evaluate_post end | shop_id={state['data'][0].get('shop_id')} | is_pass={result.get('is_pass')} | reason={result.get('reason')}")
        return {
            **state,
            'is_pass': result.get('is_pass'),
            'reason': result.get('reason'),
        }

    except Exception as e:
        logger.error(f"Error={e} | time={time.time()} | crawling_id={state['data'][0].get('crawling_id')}")
        return state

def route_after_embedding(state: State) -> str:
    """유사 게시글이 발견되면 바로 재생성으로 보내 중복을 줄인다."""
    if state.get('similar_post'):
        if state.get('retry_count', 0) > 0:
            return "evaluate_post"
        return "regenerate_post"
    return "evaluate_post"


def route_after_evaluation(state: State) -> str:
    """평가 통과 또는 최대 재시도 도달 시 그래프를 종료한다."""
    if state.get('is_pass'):
        return "end"
    if state.get('retry_count', 0) >= 2:
        return "end"
    return "regenerate_post"


def build_graph():
    """게시글 생성부터 평가까지의 LangGraph 흐름을 구성한다."""
    graph = StateGraph(State)
    graph.add_node("make_post", make_post)
    graph.add_node("make_title", make_title)
    graph.add_node("embedding", embedding)
    graph.add_node("regenerate_post", regenerate_post)
    graph.add_node("evaluate_post", evaluate_post)
    graph.add_edge(START, "make_post")
    graph.add_edge("make_post", "make_title")
    graph.add_edge("make_title", "embedding")

    # 기존 게시글과 유사하면 평가 전에 먼저 재생성한다.
    graph.add_conditional_edges(
        "embedding",
        route_after_embedding,
        {
            "regenerate_post": "regenerate_post",
            "evaluate_post": "evaluate_post",
            "end": END,
        }
    )
    graph.add_edge("regenerate_post", "make_title")

    # 평가 실패 시 최대 retry_count까지 재생성하고, 다시 제목/유사도 검사를 거친다.
    graph.add_conditional_edges(
        "evaluate_post",
        route_after_evaluation,
        {
            "regenerate_post": "regenerate_post",
            "end": END,
        }
    )
    return graph.compile()


graph = build_graph()
