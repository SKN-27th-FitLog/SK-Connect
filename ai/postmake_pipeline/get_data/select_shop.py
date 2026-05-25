from common.logging_config import set_logging
from common.connection import PGVectorStore, get_cursor
from common.constants import RESTAURANT_INFORMATION_CD
from common.text_utils import (
    latest_crawling_created_at as get_latest_crawling_created_at,
    parse_keywords,
)
from get_data.keyword_taxonomy import (
    canonicalize_signals,
    categories_of_keyword,
    primary_category,
)
from langchain_core.documents import Document
from math import log1p, sqrt
from get_data.keyword_morphology import (
    extract_keyword_actions as _extract_keyword_actions,
    extract_keyword_nouns as _extract_keyword_nouns,
    extract_keyword_signatures as _extract_keyword_signatures,
    has_containment_signal as _has_containment_signal,
    keyword_has_predicate_token as _keyword_has_predicate_token,
    keyword_has_topic as _keyword_has_topic,
    keyword_signal_values as _keyword_signal_values,
    keyword_topic_anchors as _keyword_topic_anchors,
)
import random
import time

logger = set_logging()


def _first_row(shop_data: list[dict]) -> dict:
    return shop_data[0] if shop_data else {}


def _keyword_scope(shop_data: list[dict]) -> tuple[str, int | str | None]:
    """키워드 이력 저장/조회 기준을 반환한다. 맛집은 shop_id, 그 외는 crawling_id 기준이다."""
    row = _first_row(shop_data)
    information_cd = row.get("information_cd")

    if information_cd == RESTAURANT_INFORMATION_CD:
        return "shop_id", row.get("shop_id")
    if row.get("crawling_id") is not None:
        return "crawling_id", row.get("crawling_id")
    if row.get("shop_id") is not None:
        return "shop_id", row.get("shop_id")
    return "unknown", None


def select_shop(shop_data: list[dict], positive_ratio: float = 0.7) -> bool:
    """
    긍정 댓글 수/ 음식점별 전체 댓글 수
    => 해당 값이 0.7 이상인 음식점 선별
    """
    try:
        total_count = len(shop_data)
        if not total_count:
            return False
        positive_count = sum(1 for shop in shop_data if shop.get("sentimental") == "positive")
        return positive_count / total_count >= positive_ratio
    except Exception as e:
        crawling_id = None
        if shop_data:
            crawling_id = shop_data[0].get("crawling_id")
        logger.error(f"select_shop | Error={e} | time={time.time()} | crawling_id={crawling_id}")
        return False


def select_keyword(
    shop_data: list[dict],
    keyword_ratio: float = 0.5,
    max_keywords: int = 5,
    keyword_rules: dict | None = None,
    collection_name: str = "keyword_vector",
) -> dict:
    """
    긍정 row의 keywords를 집계해 게시글 생성용 키워드와 vector 저장용 통계를 만든다.
    """
    try:
        rules = {
            # 과거 유사 키워드 누적 카운트에 따른 가중치 부스트
            "history_boost_rate": 0.03,
            "max_history_boost": 0.1,
            # 동일 키워드가 반복 등장하면 weight를 줄여 다양성 확보
            "repeat_penalty": 0.6,
            # 한 번만 등장한 키워드 weight를 약간 깎음
            "singleton_penalty": 0.7,
            # 메뉴명/대상어 + 평가가 함께 있는 키워드는 게시글 재료로 더 구체적이므로 가중
            "target_keyword_boost": 1.2,
            # 대상 없이 "맛있다/좋다"처럼 일반 평가만 있는 키워드는 대표 키워드에서 약간 후순위
            "generic_keyword_penalty": 0.85,
            # 과거 vector 조회 시 거리 컷오프
            "similarity_distance_threshold": 0.25,
            # 시그니처가 없는 키워드 배치 그룹핑 시 임베딩 거리 컷오프
            "batch_similarity_distance_threshold": 0.3,
            # 시그니처가 서로 다른 일반 평가끼리 임베딩만으로 묶을 때의 보수적 컷오프
            "strict_batch_similarity_distance_threshold": 0.18,
            # 단독 서술형 키워드 제외용 접미사 패턴 — 운영 단계에서만 설정
            "contextless_statement_suffix": None,
            "keyword_schema_version": 2,

            # 최종 weight에만 약한 랜덤 보정 적용
            # 같은 shop_id + 수집시각 + keyword 기준으로는 같은 값이 나오게 한다.
            "random_jitter_min": 0.9,
            "random_jitter_max": 1.1,
        }
        if keyword_rules:
            rules.update(keyword_rules)

        positive_rows = [shop for shop in shop_data if shop.get('sentimental') == 'positive']
        negative_rows = [shop for shop in shop_data if shop.get('sentimental') == 'negative']

        if not positive_rows:
            return {"keywords": [], "keyword_stats": [], "negative_keywords": []}

        statement_suffix = rules["contextless_statement_suffix"]
        compact_suffix = "".join(str(statement_suffix or "").split())
        raw_keyword_score = {}
        for shop in positive_rows:
            try:
                score = float(shop.get('score') or 0)
            except (TypeError, ValueError):
                score = 0.0

            for keyword in set(parse_keywords(shop)):
                compact_keyword = "".join(str(keyword).split())
                if (
                    compact_suffix
                    and " " not in str(keyword).strip()
                    and compact_keyword.endswith(compact_suffix)
                ):
                    continue
                data = raw_keyword_score.setdefault(keyword, {"batch_count": 0, "score_sum": 0.0})
                data["batch_count"] += 1
                data["score_sum"] += score

        negative_keyword_count = {}
        for shop in negative_rows:
            for keyword in set(parse_keywords(shop)):
                negative_keyword_count[keyword] = negative_keyword_count.get(keyword, 0) + 1
        negative_keywords = [
            keyword for keyword, _ in sorted(
                negative_keyword_count.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        ]

        vectorstore = PGVectorStore(collection_name=collection_name).get_vectorstore()
        keyword_score = _group_similar_keywords(
            raw_keyword_score,
            vectorstore,
            rules,
        )
        latest_crawling_created_at = get_latest_crawling_created_at(shop_data)
        keyword_stats = _build_keyword_stats(
            keyword_score,
            shop_data,
            latest_crawling_created_at,
            vectorstore,
            rules,
        )

        ratio_candidates = [
            data for data in keyword_stats
            if data["batch_count"] / len(positive_rows) >= keyword_ratio
        ]
        top_weight = max((float(data.get("final_weight") or 0) for data in keyword_stats), default=0.0)
        pool_limit = max(max_keywords * 3, 8)
        candidate_pool = []
        for data in keyword_stats:
            if len(candidate_pool) >= pool_limit:
                break
            weight = float(data.get("final_weight") or 0)
            if data in ratio_candidates or (top_weight and weight >= top_weight * 0.55):
                candidate_pool.append(data)
        if not candidate_pool:
            candidate_pool = keyword_stats[:pool_limit]

        selected_stats = []
        selected_keywords = set()
        selected_categories = {}
        if candidate_pool:
            first = candidate_pool[0]
            selected_stats.append(first)
            selected_keywords.add(first["keyword"])
            first_category = first.get("category") or next(iter(first.get("categories") or []), "general")
            selected_categories[first_category] = selected_categories.get(first_category, 0) + 1

        target_candidates = [
            data for data in candidate_pool
            if data.get("has_target_keyword") and data["keyword"] not in selected_keywords
        ]
        if target_candidates and len(selected_stats) < max_keywords:
            weights = [max(float(data.get("final_weight") or 0), 0.01) for data in target_candidates]
            picked = random.choices(target_candidates, weights=weights, k=1)[0]
            selected_stats.append(picked)
            selected_keywords.add(picked["keyword"])
            picked_category = picked.get("category") or next(iter(picked.get("categories") or []), "general")
            selected_categories[picked_category] = selected_categories.get(picked_category, 0) + 1

        while len(selected_stats) < max_keywords:
            choices = [data for data in candidate_pool if data["keyword"] not in selected_keywords]
            if not choices:
                break
            weights = []
            for data in choices:
                category = data.get("category") or next(iter(data.get("categories") or []), "general")
                weight = max(float(data.get("final_weight") or 0), 0.01)
                if data not in ratio_candidates:
                    weight *= 0.65
                if selected_categories.get(category):
                    weight /= 1 + (selected_categories[category] * 1.2)
                if not data.get("has_target_keyword") and category == "general":
                    weight *= 0.75
                weights.append(weight)
            picked = random.choices(choices, weights=weights, k=1)[0]
            selected_stats.append(picked)
            selected_keywords.add(picked["keyword"])
            picked_category = picked.get("category") or next(iter(picked.get("categories") or []), "general")
            selected_categories[picked_category] = selected_categories.get(picked_category, 0) + 1

        for data in keyword_stats:
            if len(selected_stats) >= max_keywords:
                break
            if data["keyword"] in selected_keywords:
                continue
            selected_stats.append(data)
            selected_keywords.add(data["keyword"])

        save_keyword_vector(shop_data, keyword_stats, vectorstore, collection_name)
        return {
            "keywords": [data["keyword"] for data in selected_stats],
            "keyword_stats": selected_stats,
            "negative_keywords": negative_keywords,
        }

    except Exception as e:
        crawling_id = None
        if shop_data:
            crawling_id = shop_data[0].get("crawling_id")
        logger.error(f"select_keyword | Error={e} | time={time.time()} | crawling_id={crawling_id}")
        return {"keywords": [], "keyword_stats": [], "negative_keywords": []}


def _group_similar_keywords(
    keyword_score: dict,
    vectorstore,
    rules: dict,
) -> dict:
    """
    이번 batch 안에서 의미가 가까운 키워드들을 하나의 대표 키워드 묶음으로 합친다.

    그룹핑 우선순위:
      0) 정규형(canonical) 시그니처  ← 동의어 사전 기반 (예: 맛있다=맛이좋다=맛나다)
      1) 행동·의도 시그니처
      2) 대상어가 앞에 붙은 토픽 시그니처
      3) 일반 평가 시그니처
      4) 복합 형태소 포함 관계
      5) 임베딩 코사인 거리 fallback

    대상어가 있는 평가와 일반 평가는 서로 다른 축으로 보고 자동 병합하지 않는다.
    단, 0)에서 같은 정규형이면 토픽/general 축이 달라도 우선 묶는다.
    """
    from collections import Counter

    keywords = list(keyword_score.keys())
    if not keywords:
        return {}

    keyword_predicates = {keyword: set(_extract_keyword_signatures(keyword)) for keyword in keywords}
    keyword_actions = {keyword: set(_extract_keyword_actions(keyword)) for keyword in keywords}
    keyword_nouns = {keyword: set(_extract_keyword_nouns(keyword)) for keyword in keywords}
    keyword_topic_anchors = {keyword: _keyword_topic_anchors(keyword) for keyword in keywords}
    keyword_signals = {
        keyword: _keyword_signal_values(
            keyword_predicates[keyword],
            keyword_actions[keyword],
            keyword_nouns[keyword],
        )
        for keyword in keywords
    }
    # Layer 1: 동의어 사전으로 정규화한 canonical 시그니처
    keyword_canonicals = {
        keyword: canonicalize_signals(
            keyword_predicates[keyword],
            keyword_actions[keyword],
            keyword_nouns[keyword],
        )
        for keyword in keywords
    }
    # Layer 2: 상위 카테고리(맛/가성비/서비스/분위기/양 ...)
    keyword_categories = {
        keyword: categories_of_keyword(
            keyword_canonicals[keyword],
            keyword_nouns[keyword],
        )
        for keyword in keywords
    }

    noun_counter: Counter = Counter()
    for keyword in keywords:
        for noun in keyword_topic_anchors[keyword] or keyword_nouns[keyword]:
            noun_counter[noun] += 1
    common_nouns = {noun for noun, count in noun_counter.items() if count >= 2}

    effective_signatures = {}
    keyword_scopes = {}
    for keyword in keywords:
        if keyword_actions[keyword]:
            effective_signatures[keyword] = {f"a:{action}" for action in keyword_actions[keyword]}
            keyword_scopes[keyword] = "action"
            continue
        if _keyword_has_topic(keyword):
            effective_signatures[keyword] = {f"n:{noun}" for noun in keyword_topic_anchors[keyword]}
            keyword_scopes[keyword] = "topic"
            continue
        kw_common = keyword_nouns[keyword] & common_nouns
        if kw_common:
            effective_signatures[keyword] = {f"n:{noun}" for noun in kw_common}
            keyword_scopes[keyword] = "topic"
            continue
        if keyword_predicates[keyword]:
            effective_signatures[keyword] = {f"p:{predicate}" for predicate in keyword_predicates[keyword]}
            keyword_scopes[keyword] = "general"
            continue
        effective_signatures[keyword] = set()
        keyword_scopes[keyword] = "unknown"

    embeddings = vectorstore.embeddings.embed_documents(keywords)
    embedding_map = dict(zip(keywords, embeddings))

    groups: list[dict] = []

    for keyword in keywords:
        signatures = effective_signatures[keyword]
        scope = keyword_scopes[keyword]
        embedding = embedding_map[keyword]
        canonicals = keyword_canonicals[keyword]
        categories = keyword_categories[keyword]
        matched_group = None

        # 0) 동의어 사전 기반 canonical 우선 매칭
        # 형태소 시그니처가 달라도 같은 의미면(예: 맛있다 / 맛이좋다 / 맛나다)
        # 같은 canonical 토큰이 만들어지므로 여기서 묶인다.
        if canonicals:
            for group in groups:
                if canonicals & group["canonicals"]:
                    matched_group = group
                    break

        if matched_group is None and signatures:
            for group in groups:
                if signatures & group["signatures"]:
                    matched_group = group
                    break

        if matched_group is None and keyword_signals[keyword]:
            for group in groups:
                if not _has_containment_signal(keyword_signals[keyword], group["signals"]):
                    continue
                if not _can_merge_keyword(keyword, group["keywords"], rules):
                    continue
                matched_group = group
                break

        # 시그니처/복합 관계 매칭 실패 시 임베딩 fallback
        if matched_group is None:
            best_distance = None
            for group in groups:
                distance_threshold = rules["batch_similarity_distance_threshold"]
                if signatures and group["signatures"] and not (signatures & group["signatures"]):
                    if not (scope == group["scope"] == "general"):
                        continue
                    distance_threshold = rules["strict_batch_similarity_distance_threshold"]
                if not group["embedding_count"]:
                    continue
                avg_embedding = [value / group["embedding_count"] for value in group["embedding_sum"]]
                dot = sum(left * right for left, right in zip(embedding, avg_embedding))
                left_norm = sqrt(sum(value * value for value in embedding))
                right_norm = sqrt(sum(value * value for value in avg_embedding))
                if not left_norm or not right_norm:
                    continue
                distance = 1 - (dot / (left_norm * right_norm))
                if distance <= distance_threshold:
                    if best_distance is None or distance < best_distance:
                        best_distance = distance
                        matched_group = group

        if matched_group:
            matched_group["keywords"].append(keyword)
            matched_group["signatures"] |= signatures
            matched_group["signals"] |= keyword_signals[keyword]
            matched_group["canonicals"] |= canonicals
            matched_group["categories"] |= categories
            if matched_group["scope"] == "unknown" and scope != "unknown":
                matched_group["scope"] = scope
            matched_group["embedding_sum"] = [
                left + right
                for left, right in zip(matched_group["embedding_sum"], embedding)
            ]
            matched_group["embedding_count"] += 1
            matched_group["batch_count"] += keyword_score[keyword]["batch_count"]
            matched_group["score_sum"] += keyword_score[keyword]["score_sum"]
            continue

        groups.append({
            "keywords": [keyword],
            "signatures": set(signatures),
            "signals": set(keyword_signals[keyword]),
            "canonicals": set(canonicals),
            "categories": set(categories),
            "scope": scope,
            "embedding_sum": list(embedding),
            "embedding_count": 1,
            "batch_count": keyword_score[keyword]["batch_count"],
            "score_sum": keyword_score[keyword]["score_sum"],
        })

    grouped_keyword_score = {}
    for group in groups:
        representative_keyword = max(group["keywords"], key=len)
        grouped_keyword_score[representative_keyword] = {
            "keywords": group["keywords"],
            "batch_count": group["batch_count"],
            "score_sum": group["score_sum"],
            "canonicals": sorted(group["canonicals"]),
            "categories": sorted(group["categories"]),
        }
    return grouped_keyword_score

def _apply_weight_jitter(
    weight: float,
    keyword: str,
    shop_data: list[dict],
    latest_crawling_created_at: str,
    rules: dict,
) -> float:
    """
    최종 키워드 weight에 작은 랜덤 보정을 적용한다.
    완전 랜덤이 아니라 shop_id + 수집시각 + keyword 기준으로 고정되어 재현 가능하다.
    """
    jitter_min = float(rules.get("random_jitter_min", 1.0))
    jitter_max = float(rules.get("random_jitter_max", 1.0))

    if jitter_min == 1.0 and jitter_max == 1.0:
        return weight

    if jitter_min > jitter_max:
        jitter_min, jitter_max = jitter_max, jitter_min

    scope_type, scope_id = _keyword_scope(shop_data)
    seed = (
        f"{scope_type}:{scope_id}:"
        f"{latest_crawling_created_at}:"
        f"{keyword}:"
        f"{rules.get('keyword_schema_version')}"
    )

    rng = random.Random(seed)
    return weight * rng.uniform(jitter_min, jitter_max)


def _build_keyword_stats(
    keyword_score: dict,
    shop_data: list[dict],
    latest_crawling_created_at: str,
    vectorstore,
    rules: dict,
) -> list[dict]:
    """그룹핑된 키워드에 과거 유사 키워드 이력을 반영해 최종 weight를 만든다."""
    keyword_stats = []
    statement_suffix = rules["contextless_statement_suffix"]
    compact_suffix = "".join(str(statement_suffix or "").split())
    scope_type, scope_id = _keyword_scope(shop_data)
    base_filter_metadata = {
        "sentiment": "positive",
        "keyword_schema_version": rules["keyword_schema_version"],
    }
    if scope_id is not None:
        base_filter_metadata[scope_type] = scope_id
    for keyword, data in keyword_score.items():
        batch_count = data["batch_count"]
        similar_documents = []
        filter_metadata = dict(base_filter_metadata)

        similar_results = vectorstore.similarity_search_with_score(
            keyword,
            k=20,
            filter=filter_metadata,
        )
        for document, score in similar_results:
            document_keywords = document.metadata.get("keywords") or [document.page_content]
            if isinstance(document_keywords, list):
                document_keywords = [
                    str(document_keyword).strip()
                    for document_keyword in document_keywords
                    if str(document_keyword).strip()
                ]
            else:
                document_keywords = [str(document_keywords).strip()]

            has_contextless_keyword = False
            if compact_suffix:
                for document_keyword in document_keywords:
                    compact_keyword = "".join(str(document_keyword).split())
                    if (
                        " " not in str(document_keyword).strip()
                        and compact_keyword.endswith(compact_suffix)
                    ):
                        has_contextless_keyword = True
                        break

            if (
                score <= rules["similarity_distance_threshold"]
                and not has_contextless_keyword
                and _can_merge_keyword(keyword, document_keywords, rules)
            ):
                similar_documents.append((document, document_keywords))

        historical_count = sum(
            int(document.metadata.get("batch_count") or 0)
            for document, _ in similar_documents
        )
        keywords = [keyword]
        for grouped_keyword in data.get("keywords", []):
            if not _can_merge_keyword(keyword, [grouped_keyword], rules):
                continue
            keywords.append(grouped_keyword)
        for _, document_keywords in similar_documents:
            for document_keyword in document_keywords:
                compact_keyword = "".join(str(document_keyword).split())
                if (
                    compact_suffix
                    and " " not in str(document_keyword).strip()
                    and compact_keyword.endswith(compact_suffix)
                ):
                    continue
                if not _can_merge_keyword(keyword, [document_keyword], rules):
                    continue
                keywords.append(document_keyword)

        average_score = data["score_sum"] / batch_count
        batch_weight = batch_count * average_score
        history_boost = min(
            log1p(historical_count) * rules["history_boost_rate"],
            rules["max_history_boost"],
        )

        final_weight = batch_weight * (1 + history_boost)
        if similar_documents:
            final_weight *= rules["repeat_penalty"]
        if batch_count == 1 and not historical_count:
            final_weight *= rules["singleton_penalty"]

        keywords = [str(value).strip() for value in keywords if str(value).strip()]
        representative_keyword = max(set(keywords), key=len)
        has_target_keyword = any(_keyword_has_topic(value) for value in keywords)
        is_generic_predicate_keyword = (
            not has_target_keyword
            and _keyword_has_predicate_token(representative_keyword)
            and not _extract_keyword_nouns(representative_keyword)
        )

        # Layer 1: 정규형 토큰 집합, Layer 2: 상위 카테고리
        canonicals = sorted(set(data.get("canonicals") or []))
        categories = sorted(set(data.get("categories") or []))
        # 대표 카테고리 (없으면 None) - 첫 키워드 기준
        representative_category = primary_category(
            set(canonicals),
            set(_extract_keyword_nouns(representative_keyword)),
        )

        if has_target_keyword:
            final_weight *= rules["target_keyword_boost"]
        elif is_generic_predicate_keyword:
            final_weight *= rules["generic_keyword_penalty"]

        final_weight = _apply_weight_jitter(
            final_weight,
            representative_keyword,
            shop_data,
            latest_crawling_created_at,
            rules,
        )

        keyword_stats.append({
            "keyword": representative_keyword,
            "keywords": sorted(set(keywords), key=len),
            "sentiment": "positive",
            "keyword_schema_version": rules["keyword_schema_version"],
            "batch_count": batch_count,
            "historical_count": historical_count,
            "average_score": round(average_score, 4),
            "final_weight": round(final_weight, 4),
            "latest_crawling_created_at": latest_crawling_created_at,
            "canonicals": canonicals,
            "categories": categories,
            "category": representative_category,
            "has_target_keyword": has_target_keyword,
        })
    return sorted(keyword_stats, key=lambda item: item["final_weight"], reverse=True)


def _can_merge_keyword(
    keyword: str,
    group_keywords: list[str],
    rules: dict,
) -> bool:
    """
    대상어/의도/일반 평가 축이 충돌하지 않을 때만 병합을 허용한다.
    """
    kw_predicates = set(_extract_keyword_signatures(keyword))
    kw_actions = set(_extract_keyword_actions(keyword))
    kw_nouns = set(_extract_keyword_nouns(keyword))
    kw_has_topic = _keyword_has_topic(keyword)
    kw_topic_anchors = _keyword_topic_anchors(keyword)
    kw_signals = _keyword_signal_values(kw_predicates, kw_actions, kw_nouns)
    if not kw_predicates and not kw_actions and not kw_nouns:
        return True

    group_predicates: set = set()
    group_actions: set = set()
    group_nouns: set = set()
    group_topic_anchors: set = set()
    group_signals: set = set()
    group_has_signal = False
    group_has_topic = False
    for group_keyword in group_keywords:
        g_predicates = set(_extract_keyword_signatures(group_keyword))
        g_actions = set(_extract_keyword_actions(group_keyword))
        g_nouns = set(_extract_keyword_nouns(group_keyword))
        g_has_topic = _keyword_has_topic(group_keyword)
        g_topic_anchors = _keyword_topic_anchors(group_keyword)
        group_signals |= _keyword_signal_values(g_predicates, g_actions, g_nouns)
        if g_has_topic:
            group_has_topic = True
            group_topic_anchors |= g_topic_anchors
        if g_predicates or g_actions or g_nouns:
            group_has_signal = True
            group_predicates |= g_predicates
            group_actions |= g_actions
            group_nouns |= g_nouns

    if not group_has_signal:
        return True

    if kw_has_topic != group_has_topic:
        topic_anchors = kw_topic_anchors if kw_has_topic else group_topic_anchors
        non_topic_nouns = group_nouns if kw_has_topic else kw_nouns
        if not (
            topic_anchors & non_topic_nouns
            or _has_containment_signal(topic_anchors, non_topic_nouns)
        ):
            return False

    if kw_has_topic and group_has_topic and not (kw_topic_anchors & group_topic_anchors):
        return False

    if _has_containment_signal(kw_signals, group_signals):
        return True

    if kw_actions or group_actions:
        if kw_actions & group_actions:
            return True
        return False

    if kw_topic_anchors & group_topic_anchors:
        return True
    if kw_nouns & group_nouns:
        return True
    if kw_predicates & group_predicates:
        return True
    return False


def save_keyword_vector(
    shop_data: list[dict],
    keyword_stats: list[dict],
    vectorstore,
    collection_name: str = "keyword_vector",
) -> None:
    """선택된 키워드 통계를 keyword_vector 컬렉션에 저장한다."""
    try:
        if not keyword_stats:
            return

        shop = _first_row(shop_data)
        scope_type, scope_id = _keyword_scope(shop_data)
        shop_id = shop.get("shop_id")
        crawling_id = shop.get("crawling_id")
        if scope_id is None:
            return

        documents = []
        for data in keyword_stats:
            metadata = {
                "shop_id": shop_id,
                "crawling_id": crawling_id,
                "information_cd": shop.get("information_cd"),
                "category_cd": shop.get("category_cd"),
                "keyword_scope_type": scope_type,
                "keyword_scope_id": scope_id,
                "keyword": data["keyword"],
                "keywords": data["keywords"],
                "sentiment": data["sentiment"],
                "keyword_schema_version": data["keyword_schema_version"],
                "batch_count": data["batch_count"],
                "historical_count": data["historical_count"],
                "average_score": data["average_score"],
                "final_weight": data["final_weight"],
                "latest_crawling_created_at": data["latest_crawling_created_at"],
                "canonicals": data.get("canonicals") or [],
                "categories": data.get("categories") or [],
                "category": data.get("category"),
                "has_target_keyword": data.get("has_target_keyword"),
            }
            documents.append(Document(page_content=data["keyword"], metadata=metadata))

        # 배치 내 모든 키워드는 동일한 scope·schema_version·latest_crawling_created_at를 공유하므로
        # 개별 DELETE N회 대신 keyword = ANY(%s) 배열 조건으로 단일 쿼리로 처리한다.
        keyword_names = [str(data["keyword"]) for data in keyword_stats]
        schema_version = str(keyword_stats[0]["keyword_schema_version"])
        latest_ts = str(keyword_stats[0].get("latest_crawling_created_at") or "")
        deleted_count = 0
        cursor = get_cursor(
            """
            DELETE FROM langchain_pg_embedding AS e
            USING langchain_pg_collection AS c
            WHERE e.collection_id = c.uuid
              AND c.name = %s
              AND (
                  (
                      e.cmetadata ->> 'keyword_scope_type' = %s
                      AND e.cmetadata ->> 'keyword_scope_id' = %s
                  )
                  OR (
                      %s = 'shop_id'
                      AND e.cmetadata ->> 'shop_id' = %s
                  )
                  OR (
                      %s = 'crawling_id'
                      AND e.cmetadata ->> 'crawling_id' = %s
                  )
              )
              AND e.cmetadata ->> 'keyword_schema_version' = %s
              AND e.cmetadata ->> 'keyword' = ANY(%s)
              AND e.cmetadata ->> 'latest_crawling_created_at' = %s
            """,
            (
                collection_name,
                scope_type,
                str(scope_id),
                scope_type,
                str(scope_id),
                scope_type,
                str(scope_id),
                schema_version,
                keyword_names,
                latest_ts,
            ),
        )
        if cursor:
            deleted_count = max(cursor.rowcount, 0)

        vectorstore.add_documents(documents)
        logger.info(
            f"keyword_vector inserted | scope={scope_type}:{scope_id} | "
            f"shop_id={shop_id} | crawling_id={crawling_id} | "
            f"keyword_count={len(documents)} | deleted_existing={deleted_count}"
        )
    except Exception as e:
        shop = {}
        if shop_data:
            shop = shop_data[0]
        logger.error(f"save_keyword_vector | Error={e} | time={time.time()} | shop_id={shop.get('shop_id')}")
