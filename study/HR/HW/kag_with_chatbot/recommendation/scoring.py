"""
recommendation/scoring.py — 스코어링, 다양성 보정, 중복 제거

Cypher 쿼리 결과(후보군)를 Python 레벨에서 후처리합니다.

[처리 단계]
    1. Diversity Correction : 카테고리별 중복 패널티 적용
    2. Deduplication         : ID 기반 중복 제거 (최고 점수 유지)
    3. Tie-breaking          : 동점 시 결정론적 정렬 (카테고리 > ID)

[입출력]
    입력: Cypher 쿼리 결과 리스트 (quality_score, cat_group 포함)
    출력: 최종 추천 리스트 (final_score 기준 정렬)
"""

from utils.logger import get_logger

logger = get_logger("Scoring")


def apply_diversity_penalty(candidates: list, diversity_flag: bool,
                            limit: int) -> list:
    """
    카테고리 다양성을 위한 페널티를 적용합니다.

    같은 카테고리의 식당이 너무 많이 추천되는 것을 방지합니다.
    diversity_flag가 True이면 카테고리당 최대 2개로 제한하고,
    초과 시 강력 패널티(0.5)를 부과합니다.

    [Fail-safe]
        후보가 limit*2 미만이면 Cap을 완화하여
        결과가 너무 적어지는 것을 방지합니다.

    Args:
        candidates     : Cypher 쿼리 결과 리스트 (quality_score 포함)
        diversity_flag : 다양성 요청 여부
        limit          : 최종 추천 개수

    Returns:
        final_score가 추가된 후보 리스트
    """
    MAX_PER_CAT = 2 if diversity_flag else 99
    category_counts = {}
    processed = []

    for c in candidates:
        cat = c["cat_group"]
        score = c["quality_score"]
        occurrences = category_counts.get(cat, 0)

        # Fail-safe: 후보가 적으면 Cap 완화
        effective_cap = MAX_PER_CAT
        if len(candidates) < limit * 2:
            effective_cap = 99

        # 동일 카테고리 초과 시 패널티 적용
        if occurrences >= effective_cap:
            penalty = 0.5   # 강력 패널티 (사실상 하위로 밀림)
        else:
            penalty = occurrences * 0.1  # 누적 소량 패널티

        c["final_score"] = score - penalty
        category_counts[cat] = occurrences + 1
        processed.append(c)

    return processed


def deduplicate_results(candidates: list) -> list:
    """
    ID 기반으로 중복된 추천 결과를 제거합니다.

    동일 ID가 여러 번 나타난 경우:
        1. final_score가 높은 것을 유지
        2. 점수가 같으면 카테고리명 → ID 순으로 결정론적 선택

    Args:
        candidates: diversity 패널티가 적용된 후보 리스트

    Returns:
        중복 제거된 후보 딕셔너리의 values 리스트
    """
    deduped = {}

    for c in candidates:
        rid = c["id"]
        if rid not in deduped:
            deduped[rid] = c
        else:
            existing = deduped[rid]
            # 높은 점수 우선
            if c["final_score"] > existing["final_score"]:
                deduped[rid] = c
            elif c["final_score"] == existing["final_score"]:
                # 결정론적 타이브레이킹: 카테고리 사전순 → ID 사전순
                if (c["cat_group"] < existing["cat_group"]
                        or (c["cat_group"] == existing["cat_group"]
                            and c["id"] < existing["id"])):
                    deduped[rid] = c

    return list(deduped.values())


def sort_and_limit(candidates: list, limit: int) -> list:
    """
    최종 정렬 및 개수 제한을 적용합니다.

    정렬 기준 (우선순위 순):
        1. final_score 내림차순 (높을수록 좋음)
        2. cat_group 오름차순 (사전순)
        3. id 오름차순 (결정론적 타이브레이킹)

    Args:
        candidates : 중복 제거된 후보 리스트
        limit      : 최대 반환 개수

    Returns:
        정렬 + 개수 제한된 최종 리스트
    """
    results = sorted(
        candidates,
        key=lambda x: (-x["final_score"], x["cat_group"], x["id"]),
    )
    return results[:limit]


def post_process_candidates(candidates: list, diversity_flag: bool,
                            limit: int) -> list:
    """
    Cypher 결과 후처리 파이프라인의 진입점.

    [파이프라인]
        1. apply_diversity_penalty → 카테고리 다양성 패널티
        2. deduplicate_results    → ID 중복 제거
        3. sort_and_limit         → 최종 정렬 및 개수 제한
        4. (옵션) 다양성 로그 출력

    Args:
        candidates     : Cypher 쿼리 원본 결과
        diversity_flag : 다양성 요청 여부
        limit          : 최대 반환 개수

    Returns:
        최종 추천 리스트
    """
    # 1단계: 다양성 패널티
    processed = apply_diversity_penalty(candidates, diversity_flag, limit)

    # 2단계: 중복 제거
    deduped = deduplicate_results(processed)

    # 3단계: 정렬 + 제한
    final = sort_and_limit(deduped, limit)

    # 4단계: 다양성 분포 로그
    if diversity_flag and final:
        dist = {}
        for r in final:
            dist[r["cat_group"]] = dist.get(r["cat_group"], 0) + 1
        logger.info(f"      -> [Diversity Trace] Category Distribution: {dist}")

    return final
