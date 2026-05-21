from common.logging_config import set_logging
from common.connection import PGVectorStore, get_cursor
from common.keyword_taxonomy import (
    canonicalize_signals,
    categories_of_keyword,
    primary_category,
)
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
    pending_xr: str | None = None    # 직전 어근 (XR) - 다음 XSA/XSV와 결합 후보

    for token in tokens:
        form = token.form
        tag = token.tag

        # 명사 접두사 / 명사: 복합명사 후보로 누적, 부사는 명사가 새로 오면 사라짐
        if tag in config["noun_prefix_tags"] or tag in config["noun_tags"]:
            pending_noun_parts.append(form)
            pending_mag = None
            pending_xr = None
            continue

        # 명사 파생접미사: 직전 명사구의 일부로 흡수
        if tag in config["noun_suffix_tags"] and pending_noun_parts:
            pending_noun_parts.append(form)
            continue

        # 부사: 바로 뒤에 오는 파생접미사/지정사와 결합할 후보로 보관 (명사구는 유지)
        if tag == 'MAG':
            pending_mag = form
            continue

        # 어근(XR): "깔끔/깨끗/청결"처럼 단독으로 안 쓰이고 -하/되 와 결합해 술어가 되는 토큰
        if tag == 'XR':
            pending_xr = form
            continue

        # 명사/부사/어근 → 용언 파생접미사 (하/되). MAG/XR 우선.
        if tag in config["verbalizing_tags"]:
            if pending_xr:
                signatures.append(f"{pending_xr}{form}다")
                pending_xr = None
                pending_mag = None
                pending_noun_parts = []
                continue
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
                pending_xr = None
                continue
            if pending_noun_parts:
                noun = ''.join(pending_noun_parts)
                pending_noun_parts = []
                pending_xr = None
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
                pending_xr = None
                continue
            signatures.append(f"{form}다")
            pending_noun_parts = []
            pending_mag = None
            pending_xr = None
            continue

        # 조사/어미: 명사구·부사 누적 종료
        if tag.startswith('J') or tag.startswith('E'):
            pending_noun_parts = []
            pending_mag = None
            pending_xr = None

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
    pending_xr = None
    for token in tokens:
        form = token.form
        tag = token.tag
        if tag in config["topic_noun_tags"]:
            nouns.append(form)
        if tag in config["noun_prefix_tags"] or tag in config["noun_tags"]:
            pending_noun_parts.append(form)
            pending_mag = None
            pending_xr = None
            continue
        if tag in config["noun_suffix_tags"] and pending_noun_parts:
            pending_noun_parts.append(form)
            continue
        if tag == 'MAG':
            pending_mag = form
            continue
        if tag == 'XR':
            pending_xr = form
            continue
        if tag in config["verbalizing_tags"]:
            has_predicate_token = True
            if pending_xr:
                # 어근 + 하/되 → "깔끔하다" 같은 술어. 매장 같은 컨텍스트 명사는 그대로 두고
                # actions로는 어근+하다만 기록한다.
                actions.append(f"{pending_xr}{form}다")
                pending_xr = None
                pending_mag = None
                pending_noun_parts = []
                continue
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
            pending_xr = None
            continue
        if tag in config["predicate_tags"]:
            has_predicate_token = True
            pending_noun_parts = []
            pending_mag = None
            pending_xr = None
            continue
        if tag == 'VCP':
            has_predicate_token = True
            pending_noun_parts = []
            pending_mag = None
            pending_xr = None
            continue
        if tag.startswith('J') or tag.startswith('E'):
            pending_noun_parts = []
            pending_mag = None
            pending_xr = None
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
    if _is_nominal_predicate_statement(keyword):
        return False
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


@lru_cache(maxsize=4096)
def _is_nominal_predicate_statement(keyword: str) -> bool:
    """명사 하나가 지정사로 서술된 평가 표현인지 확인한다."""
    text = str(keyword or '').strip()
    if not text:
        return False
    try:
        tokens = _get_kiwi().tokenize(text)
    except Exception as e:
        logger.error(f"_is_nominal_predicate_statement | tokenize fail | keyword={keyword} | error={e}")
        return False

    config = _get_morph_config()
    nouns = []
    has_copula = False
    has_other_predicate = False
    for token in tokens:
        if token.tag in config["topic_noun_tags"]:
            nouns.append(token.form)
            continue
        if token.tag == 'VCP':
            has_copula = True
            continue
        if token.tag in config["predicate_tags"] or token.tag in config["verbalizing_tags"]:
            has_other_predicate = True
    return has_copula and not has_other_predicate and len(nouns) == 1


def _keyword_signal_values(
    predicates: set,
    actions: set,
    nouns: set,
) -> set:
    """키워드 병합에 쓸 형태소 기반 신호를 모은다."""
    values = {
        str(value).strip()
        for value in predicates | actions | nouns
        if str(value).strip()
    }
    values |= {value[:-2] for value in values if value.endswith("이다")}
    return values


def _has_containment_signal(left_values: set, right_values: set, min_length: int = 2) -> bool:
    """복합명사/복합술어처럼 한 신호가 다른 신호를 포함하는지 확인한다."""
    for left in left_values:
        for right in right_values:
            if left == right:
                continue
            shorter, longer = sorted((left, right), key=len)
            if len(shorter) < min_length:
                continue
            if shorter in longer:
                return True
    return False


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

            keywords_value = shop.get('keywords') or ''
            if isinstance(keywords_value, str):
                keywords = [kw.strip() for kw in keywords_value.split('#') if kw.strip()]
            elif isinstance(keywords_value, list):
                keywords = [str(kw).strip() for kw in keywords_value if str(kw).strip()]
            else:
                keywords = []

            for keyword in set(keywords):
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
            keywords_value = shop.get('keywords') or ''
            if isinstance(keywords_value, str):
                keywords = [kw.strip() for kw in keywords_value.split('#') if kw.strip()]
            elif isinstance(keywords_value, list):
                keywords = [str(kw).strip() for kw in keywords_value if str(kw).strip()]
            else:
                keywords = []
            for keyword in set(keywords):
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

        selected_stats = [
            data for data in keyword_stats
            if data["batch_count"] / len(positive_rows) >= keyword_ratio
        ][:max_keywords]
        selected_keywords = {data["keyword"] for data in selected_stats}
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
    for keyword, data in keyword_score.items():
        batch_count = data["batch_count"]
        similar_documents = []
        similar_results = vectorstore.similarity_search_with_score(
            keyword,
            k=20,
            filter={
                "shop_id": shop_data[0].get("shop_id"),
                "sentiment": "positive",
                "keyword_schema_version": rules["keyword_schema_version"],
            },
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
        if has_target_keyword:
            final_weight *= rules["target_keyword_boost"]
        elif is_generic_predicate_keyword:
            final_weight *= rules["generic_keyword_penalty"]

        # Layer 1: 정규형 토큰 집합, Layer 2: 상위 카테고리
        canonicals = sorted(set(data.get("canonicals") or []))
        categories = sorted(set(data.get("categories") or []))
        # 대표 카테고리 (없으면 None) - 첫 키워드 기준
        representative_category = primary_category(
            set(canonicals),
            set(_extract_keyword_nouns(representative_keyword)),
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
                "canonicals": data.get("canonicals") or [],
                "categories": data.get("categories") or [],
                "category": data.get("category"),
                "has_target_keyword": data.get("has_target_keyword"),
            }
            documents.append(Document(page_content=data["keyword"], metadata=metadata))

        deleted_count = 0
        for data in keyword_stats:
            cursor = get_cursor(
                """
                DELETE FROM langchain_pg_embedding AS e
                USING langchain_pg_collection AS c
                WHERE e.collection_id = c.uuid
                  AND c.name = %s
                  AND e.cmetadata ->> 'shop_id' = %s
                  AND e.cmetadata ->> 'keyword_schema_version' = %s
                  AND e.cmetadata ->> 'keyword' = %s
                  AND e.cmetadata ->> 'latest_crawling_created_at' = %s
                """,
                (
                    collection_name,
                    str(shop_id),
                    str(data["keyword_schema_version"]),
                    str(data["keyword"]),
                    str(data.get("latest_crawling_created_at") or ""),
                ),
            )
            if cursor:
                deleted_count += max(cursor.rowcount, 0)

        vectorstore.add_documents(documents)
        logger.info(
            f"keyword_vector inserted | shop_id={shop_id} | "
            f"keyword_count={len(documents)} | deleted_existing={deleted_count}"
        )
    except Exception as e:
        shop = {}
        if shop_data:
            shop = shop_data[0]
        logger.error(f"save_keyword_vector | Error={e} | time={time.time()} | shop_id={shop.get('shop_id')}")
