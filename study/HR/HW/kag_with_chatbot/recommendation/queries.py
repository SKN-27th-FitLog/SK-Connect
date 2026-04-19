"""
recommendation/queries.py — Cypher 쿼리 빌더

Neo4j에 전달할 Cypher 쿼리 문자열을 조립합니다.
SQL의 Query Builder 패턴과 유사하게,
조건절(WHERE), 필터절, 스코어링절을 개별 함수로 분리합니다.

[설계 원칙]
    - 쿼리 로직과 비즈니스 로직(스코어링, 다양성)을 분리합니다.
    - 각 절(clause)을 독립적으로 조립하여 유지보수성을 높입니다.
    - review_count 등 존재하지 않는 필드에 의존하지 않습니다.

[사용처]
    recommendation/engines.py의 recommend_dual_constraint에서 호출
"""


def build_exclusion_clauses(params: dict) -> list:
    """
    제외 조건(Exclusion) WHERE 절을 생성합니다.

    제외 대상:
        - viewed_ids       : 이미 본 식당 ID
        - excluded_names   : 명시적으로 제외된 식당명
        - excluded_categories : 제외 카테고리 (태그 기반)
        - negative_keywords   : 부정 키워드 (태그+이름 기반)

    Args:
        params: 정규화된 파라미터 딕셔너리

    Returns:
        WHERE 절 문자열 리스트
    """
    where_clauses = [
        "NOT r.id IN $viewed_ids",
        "NOT any(ex_name IN $excluded_names WHERE r.name CONTAINS ex_name)",
    ]

    if params.get("excluded_categories"):
        where_clauses.append(
            "NOT any(ex_cat IN $excluded_categories WHERE "
            "EXISTS { (r)-[:BELONGS_TO|HAS_TAG]->(:Tag {name: ex_cat}) })"
        )

    if params.get("negative_keywords"):
        where_clauses.append(
            "NOT any(ex_kw IN $negative_keywords WHERE "
            "EXISTS { (r)-[:HAS_TAG]->(t:Tag) WHERE t.name CONTAINS ex_kw } "
            "OR r.name CONTAINS ex_kw)"
        )

    return where_clauses


def build_positive_filters(params: dict) -> list:
    """
    긍정 필터(Positive Filter) 절을 생성합니다.

    필터 대상:
        - area_name          : 지역 필터 (LOCATED_IN 관계)
        - category_name      : 카테고리 필터 (BELONGS_TO|HAS_TAG 관계)
        - inferred_categories : 추론된 카테고리 (OR 조건)

    Args:
        params: 정규화된 파라미터 딕셔너리

    Returns:
        AND 절 문자열 리스트
    """
    pos_filters = []

    if params.get("area_name"):
        pos_filters.append("(r)-[:LOCATED_IN]->(:Area {name: $area_name})")

    cat_logic = []
    if params.get("category_name"):
        cat_logic.append(
            "(r)-[:BELONGS_TO|HAS_TAG]->(:Tag {name: $category_name})"
        )
    elif params.get("inferred_categories"):
        cat_logic.append(
            "any(cat IN $inferred_categories WHERE "
            "(r)-[:BELONGS_TO|HAS_TAG]->(:Tag {name: cat}))"
        )

    if cat_logic:
        pos_filters.append("(" + " OR ".join(cat_logic) + ")")

    return pos_filters


def build_scoring_clause() -> str:
    """
    스코어링 절을 생성합니다.

    [스코어링 구성요소]
        1. norm_rating        : 평점 정규화 (3.5~5.0 → 0.0~1.0)
        2. keyword_match_score: 키워드 일치 점수 (이름 0.5 + 태그 0.1/개)
        3. stability_boost    : 안정 구간 가산점 (3.5~4.2 → +0.2)
        4. signal_boost       : 랭킹 시그널 가산점 (이름에 시그널 포함 시)

    [최종 점수 = 0.5*rating + 0.3*keyword + signal + stability]

    Returns:
        Cypher WITH 절 문자열
    """
    return """
    WITH r, matched_tags, kws, signals, discovery_mode,
         coalesce(r.bayesian_rating, r.rating, 3.5) AS raw_rating

    WITH r, matched_tags, signals, discovery_mode, raw_rating,
         (CASE WHEN (raw_rating - 3.5) / 1.5 > 1.0 THEN 1.0
               WHEN (raw_rating - 3.5) / 1.5 < 0.0 THEN 0.0
               ELSE (raw_rating - 3.5) / 1.5 END) AS norm_rating,
         (CASE WHEN any(kw IN kws WHERE r.name CONTAINS kw) THEN 0.5 ELSE 0.0 END)
         + (size(matched_tags) * 0.1) AS keyword_match_score

    // Stability Score: 3.5~4.2 구간에 가산점 (Stability Axis 초기 휴리스틱)
    WITH r, norm_rating, keyword_match_score, discovery_mode, signals,
         (CASE WHEN raw_rating >= 3.5 AND raw_rating <= 4.2 THEN 0.2 ELSE 0.0 END)
         AS stability_boost

    WITH r, norm_rating, keyword_match_score, discovery_mode, signals, stability_boost,
         (CASE WHEN reduce(s = 0.0, sig IN signals |
            s + (CASE WHEN r.name CONTAINS sig THEN 0.2 ELSE 0.0 END)) > 0.5
               THEN 0.5
               ELSE reduce(s = 0.0, sig IN signals |
            s + (CASE WHEN r.name CONTAINS sig THEN 0.2 ELSE 0.0 END))
          END) AS signal_boost

    // Total Score (0.5 Rating / 0.3 Keyword & Signal)
    WITH r, (0.5 * norm_rating + 0.3 * keyword_match_score
             + signal_boost + stability_boost) AS quality_score,
         norm_rating, discovery_mode
    """


def build_grouping_clause() -> str:
    """
    결과 그룹화 및 최종 반환 절을 생성합니다.

    [처리 순서]
        1. 품질 점수 임계값 적용 (DISCOVERY: 0.0, 일반: 0.2)
        2. BELONGS_TO 태그를 수집하여 카테고리 그룹 결정
        3. 점수 내림차순 정렬
        4. LIMIT 적용

    Returns:
        Cypher 절 문자열
    """
    return """
    OPTIONAL MATCH (r)-[:BELONGS_TO]->(bt:Tag)
    WHERE bt.name IS NOT NULL
    WITH r, quality_score, bt.name AS tag_name ORDER BY tag_name
    WITH r, quality_score, collect(tag_name) AS all_tags
    WITH r, quality_score, all_tags, coalesce(all_tags[0], '기타') AS cat_group
    ORDER BY quality_score DESC
    LIMIT $limit_n

    RETURN r.name AS name, r.id AS id, r.address AS address,
           quality_score, cat_group,
           coalesce(r.bayesian_rating, r.rating) AS rating,
           all_tags
    """


def build_dual_constraint_query(params: dict, keyword_values: list,
                                absolute_keywords: list,
                                ranking_signals: list,
                                top_n_limit: int) -> str:
    """
    전체 Dual-Constraint 쿼리를 조립합니다.

    [쿼리 구조]
        1. MATCH (r:Restaurant)
        2. WHERE [제외 조건]
        3. AND [긍정 필터]
        4. AND [ABSOLUTE 키워드 필수 조건]
        5. OPTIONAL MATCH [태그 부스트]
        6. WITH [스코어링]
        7. WHERE [임계값]
        8. [그룹화 + RETURN]

    Args:
        params            : 정규화된 파라미터 딕셔너리
        keyword_values    : 키워드 값 리스트
        absolute_keywords : ABSOLUTE 강도 키워드 리스트
        ranking_signals   : 랭킹 시그널 리스트
        top_n_limit       : 최대 후보 수

    Returns:
        조립된 Cypher 쿼리 문자열
    """
    clauses = []

    # 1. Base Match
    clauses.append("MATCH (r:Restaurant)")

    # 2. Exclusion
    where_clauses = build_exclusion_clauses(params)
    clauses.append("WHERE " + " AND ".join(where_clauses))

    # 3. Positive Filters
    pos_filters = build_positive_filters(params)
    if pos_filters:
        clauses.append("AND " + " AND ".join(pos_filters))

    # 4. Absolute Keywords
    if absolute_keywords:
        clauses.append(
            "AND ALL(abs_kw IN $absolute_keywords WHERE "
            "EXISTS { (r)-[:BELONGS_TO|HAS_TAG]->(t:Tag) "
            "WHERE t.name CONTAINS abs_kw } OR r.name CONTAINS abs_kw)"
        )

    # 5. Tag Boost
    clauses.append("OPTIONAL MATCH (r)-[:HAS_TAG]->(t_boost:Tag)")
    clauses.append(
        "WHERE any(kw IN $keyword_values WHERE t_boost.name CONTAINS kw) "
        "OR any(sig IN $ranking_signals WHERE t_boost.name CONTAINS sig)"
    )
    clauses.append(
        "WITH r, collect(DISTINCT t_boost.name) AS matched_tags, "
        "$keyword_values AS kws, $ranking_signals AS signals, "
        "$is_discovery AS discovery_mode"
    )

    # 6. Scoring
    clauses.append(build_scoring_clause())

    # 7. Threshold
    clauses.append(
        "WHERE (discovery_mode AND norm_rating >= 0.0) "
        "OR (NOT discovery_mode AND quality_score >= 0.2)"
    )

    # 8. Grouping + Return
    clauses.append(build_grouping_clause())

    return "\n".join(clauses)


# ═════════════════════════════════════════════
# 단순 쿼리 (Level 3, ID 검색 등)
# ═════════════════════════════════════════════

LEVEL3_QUERY = """
MATCH (r:Restaurant)
WHERE ((r)-[:LOCATED_IN]->(:Area {name: $area_name}) OR $area_name IS NULL)
AND NOT r.id IN $viewed_ids
AND NOT any(ex_name IN $excluded_names WHERE r.name CONTAINS ex_name)

// Deterministic Category Grouping
OPTIONAL MATCH (r)-[:BELONGS_TO]->(bt:Tag)
WHERE bt.name IS NOT NULL
WITH r, bt.name AS tag_name ORDER BY tag_name
WITH r, collect(tag_name) AS all_tags
WITH r, coalesce(all_tags[0], '기타') AS cat_group

RETURN r.name AS name, coalesce(r.bayesian_rating, r.rating) AS rating,
       '추천 맛집' AS reason, r.address AS address, r.id AS id, cat_group
ORDER BY rating DESC, cat_group ASC, id ASC
LIMIT $limit
"""

BY_IDS_QUERY = """
UNWIND $ids AS target_id
WITH DISTINCT target_id
MATCH (r:Restaurant {id: target_id})

// Deterministic Category Grouping
OPTIONAL MATCH (r)-[:BELONGS_TO]->(bt:Tag)
WHERE bt.name IS NOT NULL
WITH r, bt.name AS tag_name ORDER BY tag_name
WITH r, collect(tag_name) AS all_tags
WITH r, coalesce(all_tags[0], '기타') AS cat_group

RETURN r.name AS name, coalesce(r.bayesian_rating, r.rating) AS rating,
       r.address AS address, r.id AS id, '과거 추천 항목' AS reason, cat_group
ORDER BY rating DESC, cat_group ASC, id ASC
"""
