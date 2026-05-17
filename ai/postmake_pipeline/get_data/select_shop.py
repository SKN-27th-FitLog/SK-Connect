from common.logging_config import set_logging
from common.connection import PGVectorStore
from langchain_core.documents import Document
from math import log1p, sqrt
from functools import lru_cache
from kiwipiepy import Kiwi
import time

logger = set_logging()

@lru_cache(maxsize=1)
def _get_kiwi() -> Kiwi:
    return Kiwi()


@lru_cache(maxsize=1)
def _get_morph_config() -> dict:
    """형태소 태그와 시그니처 추출 규칙을 반환한다."""
    return {
        "noun_tags": {'NNG', 'NNP', 'NNB'},
        "topic_noun_tags": {'NNG', 'NNP'},
        "noun_prefix_tags": {'XPN'},
        "noun_suffix_tags": {'XSN'},
        "predicate_tags": {'VV', 'VA', 'VX'},
        "verbalizing_tags": {'XSV', 'XSA'},
        "generic_predicate_stems": {'있', '없', '하', '되', '이', '같'},
    }


@lru_cache(maxsize=4096)
def _extract_keyword_signatures(keyword: str) -> tuple[str, ...]:
    """
    형태소 분석으로 키워드의 의미 시그니처(술어 기반)를 추출.
    """
    text = str(keyword or '').strip()
    if not text:
        return ()
    try:
        tokens = _get_kiwi().tokenize(text)
    except Exception as e:
        logger.error(f"_extract_keyword_signatures | tokenize fail | keyword={keyword} | error={e}")
        return ()

    config = _get_morph_config()
    signatures: list[str] = []
    pending_noun_parts: list[str] = []
    pending_mag: str | None = None  # 직전에 등장한 부사 (다음 XSV/XSA/VCP와 결합 후보)

    for token in tokens:
        form = token.form
        tag = token.tag

        # 명사 접두사 / 명사: 복합명사 후보로 누적, 부사는 명사가 새로 오면 사라짐
        if tag in config["noun_prefix_tags"] or tag in config["noun_tags"]:
            pending_noun_parts.append(form)
            pending_mag = None
            continue

        # 명사 파생접미사: 직전 명사구의 일부로 흡수
        if tag in config["noun_suffix_tags"] and pending_noun_parts:
            pending_noun_parts.append(form)
            continue

        # 부사: 바로 뒤에 오는 파생접미사/지정사와 결합할 후보로 보관 (명사구는 유지)
        if tag == 'MAG':
            pending_mag = form
            continue

        # 명사/부사 → 용언 파생접미사 (하/되). MAG 우선.
        if tag in config["verbalizing_tags"]:
            if pending_mag:
                signatures.append(f"{pending_mag}{form}다")
                pending_mag = None
                continue
            if pending_noun_parts:
                noun = ''.join(pending_noun_parts)
                pending_noun_parts = []
                signatures.append(f"{noun}{form}다")
                continue
            continue

        # 긍정 지정사(이/VCP): '이다' 형태로 결합
        if tag == 'VCP':
            if pending_mag:
                signatures.append(f"{pending_mag}이다")
                pending_mag = None
                pending_noun_parts = []
                continue
            if pending_noun_parts:
                noun = ''.join(pending_noun_parts)
                pending_noun_parts = []
                signatures.append(f"{noun}이다")
                continue
            continue

        # 형용사/동사/보조용언 어간
        if tag in config["predicate_tags"]:
            if form in config["generic_predicate_stems"] and pending_noun_parts:
                noun = ''.join(pending_noun_parts)
                signatures.append(f"{noun}_{form}다")
                pending_noun_parts = []
                pending_mag = None
                continue
            signatures.append(f"{form}다")
            pending_noun_parts = []
            pending_mag = None
            continue

        # 조사/어미: 명사구·부사 누적 종료
        if tag.startswith('J') or tag.startswith('E'):
            pending_noun_parts = []
            pending_mag = None

    # 술어를 못 찾고 명사구만 남으면 명사구를 시그니처로 사용
    if not signatures and pending_noun_parts:
        signatures.append(''.join(pending_noun_parts))

    return tuple(signatures)


@lru_cache(maxsize=4096)
def _extract_keyword_nouns(keyword: str) -> tuple[str, ...]:
    """키워드에서 등장한 일반/고유 명사 어절을 순서대로 추출한다."""
    text = str(keyword or '').strip()
    if not text:
        return ()
    try:
        tokens = _get_kiwi().tokenize(text)
    except Exception as e:
        logger.error(f"_extract_keyword_nouns | tokenize fail | keyword={keyword} | error={e}")
        return ()
    config = _get_morph_config()
    return tuple(token.form for token in tokens if token.tag in config["topic_noun_tags"])


@lru_cache(maxsize=4096)
def _extract_keyword_actions(keyword: str) -> tuple[str, ...]:
    """명사/부사에서 파생된 행동·의도 표현만 추출한다."""
    text = str(keyword or '').strip()
    if not text:
        return ()
    try:
        tokens = _get_kiwi().tokenize(text)
    except Exception as e:
        logger.error(f"_extract_keyword_actions | tokenize fail | keyword={keyword} | error={e}")
        return ()

    config = _get_morph_config()
    actions = []
    nouns = []
    has_predicate_token = False
    pending_noun_parts = []
    pending_mag = None
    for token in tokens:
        form = token.form
        tag = token.tag
        if tag in config["topic_noun_tags"]:
            nouns.append(form)
        if tag in config["noun_prefix_tags"] or tag in config["noun_tags"]:
            pending_noun_parts.append(form)
            pending_mag = None
            continue
        if tag in config["noun_suffix_tags"] and pending_noun_parts:
            pending_noun_parts.append(form)
            continue
        if tag == 'MAG':
            pending_mag = form
            continue
        if tag in config["verbalizing_tags"]:
            has_predicate_token = True
            if pending_mag:
                actions.append(f"{pending_mag}{form}다")
                pending_mag = None
                continue
            if pending_noun_parts:
                actions.append(f"{''.join(pending_noun_parts)}{form}다")
                pending_noun_parts = []
                continue
            continue
        if tag == 'VV':
            has_predicate_token = True
            if pending_mag:
                actions.append(f"{pending_mag}{form}다")
            pending_noun_parts = []
            pending_mag = None
            continue
        if tag in config["predicate_tags"]:
            has_predicate_token = True
            pending_noun_parts = []
            pending_mag = None
            continue
        if tag == 'VCP':
            has_predicate_token = True
            pending_noun_parts = []
            pending_mag = None
            continue
        if tag.startswith('J') or tag.startswith('E'):
            pending_noun_parts = []
            pending_mag = None
    if not actions and not has_predicate_token and nouns:
        actions.append(''.join(nouns))
    return tuple(actions)


@lru_cache(maxsize=4096)
def _keyword_starts_with_noun(keyword: str) -> bool:
    """첫 의미 단위가 명사 계열인지 확인한다."""
    text = str(keyword or '').strip()
    if not text:
        return False
    try:
        tokens = _get_kiwi().tokenize(text)
    except Exception as e:
        logger.error(f"_keyword_starts_with_noun | tokenize fail | keyword={keyword} | error={e}")
        return False
    config = _get_morph_config()
    for token in tokens:
        if token.tag.startswith('J') or token.tag.startswith('E'):
            continue
        return token.tag in config["noun_tags"] or token.tag in config["noun_prefix_tags"]
    return False


@lru_cache(maxsize=4096)
def _keyword_has_predicate_token(keyword: str) -> bool:
    """키워드 안에 실제 술어/파생 술어가 있는지 확인한다."""
    text = str(keyword or '').strip()
    if not text:
        return False
    try:
        tokens = _get_kiwi().tokenize(text)
    except Exception as e:
        logger.error(f"_keyword_has_predicate_token | tokenize fail | keyword={keyword} | error={e}")
        return False
    config = _get_morph_config()
    for token in tokens:
        if token.tag in config["predicate_tags"]:
            return True
        if token.tag in config["verbalizing_tags"]:
            return True
        if token.tag == 'VCP':
            return True
    return False


def _keyword_has_topic(keyword: str) -> bool:
    """대상어가 앞에 붙은 키워드인지 판단한다."""
    return (
        _keyword_starts_with_noun(keyword)
        and _keyword_has_predicate_token(keyword)
        and bool(_extract_keyword_nouns(keyword))
    )


def _keyword_topic_anchors(keyword: str) -> set:
    """대상어 그룹핑에 사용할 대표 명사를 반환한다."""
    nouns = _extract_keyword_nouns(keyword)
    if _keyword_has_topic(keyword) and nouns:
        return {nouns[0]}
    return set()


def select_shop(shop_data: list[dict], positive_ratio: float = 0.7) -> bool:
    """
    긍정 댓글 수/ 음식점별 전체 댓글 수
    => 해당 값이 0.7 이상인 음식점 선별
    """
    try:
        positive_count = 0
        total_count = 0

        # 매장 단위로 모인 analysis row에서 긍정 비율을 계산한다.
        for shop in shop_data:
            if shop['sentimental'] == 'positive':
                positive_count += 1
            total_count += 1
        if not total_count:
            return False
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
        rules = _resolve_keyword_rules(keyword_rules)
        positive_rows = [shop for shop in shop_data if shop.get('sentimental') == 'positive']
        negative_rows = [shop for shop in shop_data if shop.get('sentimental') == 'negative']

        if not positive_rows:
            return {"keywords": [], "keyword_stats": [], "negative_keywords": []}

        raw_keyword_score = _count_positive_keywords(positive_rows, rules)
        negative_keywords = _count_negative_keywords(negative_rows)
        vectorstore = PGVectorStore(collection_name=collection_name).get_vectorstore()
        keyword_score = _group_similar_keywords(
            raw_keyword_score,
            vectorstore,
            rules,
        )
        latest_crawling_created_at = max(
            str(shop.get("crawling_created_at") or shop.get("created_dt") or "")
            for shop in shop_data
        )
        keyword_stats = _build_keyword_stats(
            keyword_score,
            shop_data,
            latest_crawling_created_at,
            vectorstore,
            rules,
        )
        selected_stats = _select_keyword_stats(
            keyword_stats,
            len(positive_rows),
            keyword_ratio,
            max_keywords,
        )

        save_keyword_vector(shop_data, keyword_stats, vectorstore)
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


def _resolve_keyword_rules(keyword_rules: dict | None) -> dict:
    """키워드 병합 기준을 한 곳에서 정리한다."""
    rules = {
        # 과거 유사 키워드 누적 카운트에 따른 가중치 부스트
        "history_boost_rate": 0.03,
        "max_history_boost": 0.1,
        # 동일 키워드가 반복 등장하면 weight를 줄여 다양성 확보
        "repeat_penalty": 0.6,
        # 한 번만 등장한 키워드 weight를 약간 깎음
        "singleton_penalty": 0.7,
        # 과거 vector 조회 시 거리 컷오프
        "similarity_distance_threshold": 0.25,
        # 시그니처가 없는 키워드 배치 그룹핑 시 임베딩 거리 컷오프
        "batch_similarity_distance_threshold": 0.35,
        # 단독 서술형 키워드 제외용 접미사 패턴 — 운영 단계에서만 설정
        "contextless_statement_suffix": None,
        "keyword_schema_version": 2,
    }
    if keyword_rules:
        rules.update(keyword_rules)
    return rules


def _split_keywords(keywords) -> list[str]:
    """keywords 컬럼 값을 # 기준 리스트로 정리한다."""
    if isinstance(keywords, str):
        return [kw.strip() for kw in keywords.split('#') if kw.strip()]
    if isinstance(keywords, list):
        return [str(kw).strip() for kw in keywords if str(kw).strip()]
    return []


def _safe_float(value) -> float:
    """score가 비어 있어도 계산이 끊기지 않게 숫자로 변환한다."""
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _count_positive_keywords(positive_rows: list[dict], rules: dict) -> dict:
    """이번 batch의 positive row에서 키워드별 등장 수와 score 합계를 계산한다."""
    keyword_score = {}
    for shop in positive_rows:
        score = _safe_float(shop.get('score'))
        for keyword in set(_split_keywords(shop.get('keywords') or '')):
            if _is_contextless_statement(keyword, rules["contextless_statement_suffix"]):
                continue
            data = keyword_score.setdefault(keyword, {"batch_count": 0, "score_sum": 0.0})
            data["batch_count"] += 1
            data["score_sum"] += score
    return keyword_score


def _count_negative_keywords(negative_rows: list[dict]) -> list[str]:
    """negative row의 키워드는 프롬프트에서 피할 요소로만 사용한다."""
    keyword_count = {}
    for shop in negative_rows:
        for keyword in set(_split_keywords(shop.get('keywords') or '')):
            keyword_count[keyword] = keyword_count.get(keyword, 0) + 1
    return [
        keyword for keyword, _ in sorted(
            keyword_count.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    ]


def _group_similar_keywords(
    keyword_score: dict,
    vectorstore,
    rules: dict,
) -> dict:
    """
    이번 batch 안에서 의미가 가까운 키워드들을 하나의 대표 키워드 묶음으로 합친다.

    그룹핑 우선순위:
      1) 행동·의도 시그니처
      2) 대상어가 앞에 붙은 토픽 시그니처
      3) 일반 평가 시그니처
      4) 임베딩 코사인 거리 fallback

    대상어가 있는 평가와 일반 평가는 서로 다른 축으로 보고 자동 병합하지 않는다.
    """
    from collections import Counter

    keywords = list(keyword_score.keys())
    if not keywords:
        return {}

    keyword_predicates = {keyword: set(_extract_keyword_signatures(keyword)) for keyword in keywords}
    keyword_actions = {keyword: set(_extract_keyword_actions(keyword)) for keyword in keywords}
    keyword_nouns = {keyword: set(_extract_keyword_nouns(keyword)) for keyword in keywords}
    keyword_topic_anchors = {keyword: _keyword_topic_anchors(keyword) for keyword in keywords}

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
        matched_group = None

        if signatures:
            for group in groups:
                if signatures & group["signatures"]:
                    matched_group = group
                    break

        # 3차: 시그니처 매칭 실패 시 임베딩 fallback
        if matched_group is None:
            best_distance = None
            for group in groups:
                if signatures and group["signatures"] and not (signatures & group["signatures"]):
                    if not (
                        scope == group["scope"]
                        and scope in {"action", "general"}
                    ):
                        continue
                if not group["embedding_count"]:
                    continue
                avg_embedding = [value / group["embedding_count"] for value in group["embedding_sum"]]
                dot = sum(left * right for left, right in zip(embedding, avg_embedding))
                left_norm = sqrt(sum(value * value for value in embedding))
                right_norm = sqrt(sum(value * value for value in avg_embedding))
                if not left_norm or not right_norm:
                    continue
                distance = 1 - (dot / (left_norm * right_norm))
                if distance <= rules["batch_similarity_distance_threshold"]:
                    if best_distance is None or distance < best_distance:
                        best_distance = distance
                        matched_group = group

        if matched_group:
            matched_group["keywords"].append(keyword)
            matched_group["signatures"] |= signatures
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
        }
    return grouped_keyword_score


def _build_keyword_stats(
    keyword_score: dict,
    shop_data: list[dict],
    latest_crawling_created_at: str,
    vectorstore,
    rules: dict,
) -> list[dict]:
    """그룹핑된 키워드에 과거 유사 키워드 이력을 반영해 최종 weight를 만든다."""
    keyword_stats = []
    for keyword, data in keyword_score.items():
        batch_count = data["batch_count"]
        similar_documents = _get_similar_keyword_documents(
            keyword,
            shop_data[0].get("shop_id"),
            vectorstore,
            rules,
        )
        historical_count = sum(
            int(document.metadata.get("batch_count") or 0)
            for document in similar_documents
        )
        keywords = [keyword]
        for grouped_keyword in data.get("keywords", []):
            if not _can_merge_keyword(keyword, [grouped_keyword], rules):
                continue
            keywords.append(grouped_keyword)
        for document in similar_documents:
            for document_keyword in _get_document_keywords(document):
                if _is_contextless_statement(document_keyword, rules["contextless_statement_suffix"]):
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
        })
    return sorted(keyword_stats, key=lambda item: item["final_weight"], reverse=True)


def _get_similar_keyword_documents(keyword: str, shop_id: int, vectorstore, rules: dict) -> list:
    """keyword_vector에서 같은 가게의 유사 키워드 이력을 가져온다."""
    similar_documents = vectorstore.similarity_search_with_score(
        keyword,
        k=20,
        filter={
            "shop_id": shop_id,
            "sentiment": "positive",
            "keyword_schema_version": rules["keyword_schema_version"],
        },
    )
    return [
        document
        for document, score in similar_documents
        if score <= rules["similarity_distance_threshold"]
        and not any(
            _is_contextless_statement(document_keyword, rules["contextless_statement_suffix"])
            for document_keyword in _get_document_keywords(document)
        )
        and _can_merge_keyword(
            keyword,
            _get_document_keywords(document),
            rules,
        )
    ]


def _select_keyword_stats(
    keyword_stats: list[dict],
    positive_row_count: int,
    keyword_ratio: float,
    max_keywords: int,
) -> list[dict]:
    """기준 통과 키워드를 먼저 고르고, 부족하면 weight 순으로 채운다."""
    candidate_stats = [
        data for data in keyword_stats
        if data["batch_count"] / positive_row_count >= keyword_ratio
    ]
    selected_stats = candidate_stats[:max_keywords]
    selected_keywords = {data["keyword"] for data in selected_stats}
    for data in keyword_stats:
        if len(selected_stats) >= max_keywords:
            break
        if data["keyword"] in selected_keywords:
            continue
        selected_stats.append(data)
        selected_keywords.add(data["keyword"])
    return selected_stats


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
    if not kw_predicates and not kw_actions and not kw_nouns:
        return True

    group_predicates: set = set()
    group_actions: set = set()
    group_nouns: set = set()
    group_topic_anchors: set = set()
    group_has_signal = False
    group_has_topic = False
    for group_keyword in group_keywords:
        g_predicates = set(_extract_keyword_signatures(group_keyword))
        g_actions = set(_extract_keyword_actions(group_keyword))
        g_nouns = set(_extract_keyword_nouns(group_keyword))
        if _keyword_has_topic(group_keyword):
            group_has_topic = True
            group_topic_anchors |= _keyword_topic_anchors(group_keyword)
        if g_predicates or g_actions or g_nouns:
            group_has_signal = True
            group_predicates |= g_predicates
            group_actions |= g_actions
            group_nouns |= g_nouns

    if not group_has_signal:
        return True

    if kw_actions or group_actions:
        if kw_actions & group_actions:
            return True
        if kw_actions and group_actions:
            return True
        return False

    if kw_has_topic != group_has_topic and not (kw_nouns & group_nouns):
        return False

    if kw_has_topic and group_has_topic and not (kw_topic_anchors & group_topic_anchors):
        return False

    if kw_topic_anchors & group_topic_anchors:
        return True
    if kw_nouns & group_nouns:
        return True
    if kw_predicates & group_predicates:
        return True
    if not kw_has_topic and not group_has_topic and kw_predicates and group_predicates:
        return True
    return False


def _get_document_keywords(document) -> list[str]:
    """keyword_vector metadata의 원본 키워드 목록을 리스트로 정리한다."""
    document_keywords = document.metadata.get("keywords") or [document.page_content]
    if isinstance(document_keywords, list):
        return [str(keyword).strip() for keyword in document_keywords if str(keyword).strip()]
    return [str(document_keywords).strip()]


def _is_contextless_statement(keyword: str, statement_suffix: str) -> bool:
    """대상 없이 단독 서술형으로만 들어온 키워드는 게시글 재료에서 제외한다."""
    if not statement_suffix:
        return False
    keyword_text = str(keyword).strip()
    if " " in keyword_text:
        return False
    compact_keyword = "".join(str(keyword).split())
    compact_suffix = "".join(str(statement_suffix).split())
    if not compact_suffix:
        return False
    if compact_keyword.endswith(compact_suffix):
        return True
    return False


def save_keyword_vector(shop_data: list[dict], keyword_stats: list[dict], vectorstore) -> None:
    """선택된 키워드 통계를 keyword_vector 컬렉션에 저장한다."""
    try:
        if not keyword_stats:
            return

        shop = {}
        if shop_data:
            shop = shop_data[0]
        shop_id = shop.get("shop_id")
        if shop_id is None:
            return

        documents = []
        for data in keyword_stats:
            metadata = {
                "shop_id": shop_id,
                "keyword": data["keyword"],
                "keywords": data["keywords"],
                "sentiment": data["sentiment"],
                "keyword_schema_version": data["keyword_schema_version"],
                "batch_count": data["batch_count"],
                "historical_count": data["historical_count"],
                "average_score": data["average_score"],
                "final_weight": data["final_weight"],
                "latest_crawling_created_at": data["latest_crawling_created_at"],
            }
            documents.append(Document(page_content=data["keyword"], metadata=metadata))

        vectorstore.add_documents(documents)
        logger.info(
            f"keyword_vector inserted | shop_id={shop_id} | keyword_count={len(documents)}"
        )
    except Exception as e:
        shop = {}
        if shop_data:
            shop = shop_data[0]
        logger.error(f"save_keyword_vector | Error={e} | time={time.time()} | shop_id={shop.get('shop_id')}")
