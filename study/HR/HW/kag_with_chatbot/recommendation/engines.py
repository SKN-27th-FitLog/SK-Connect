"""
recommendation/engines.py — 추천 엔진 메인 클래스

Neo4j 기반 맛집 추천의 핵심 비즈니스 로직을 담당합니다.

[아키텍처]
    RecommendationEngine
        ├── queries.py  : Cypher 쿼리 조립
        ├── scoring.py  : 후처리 (다양성, 중복제거, 정렬)
        └── engines.py  : 오케스트레이션 (이 파일)

[제공 메서드]
    - recommend_dual_constraint : 카테고리 필터 + 키워드 랭킹 이중 제약 검색
    - recommend_level_3         : 범위 확장형 기본 검색 (Level 3)
    - get_restaurants_by_ids    : ID 기반 검색 (순서 보존)
    - update_user_interaction   : 좋아요/싫어요 인터랙션 기록
    - get_disliked_tags         : 사용자가 싫어한 태그 조회

[사용처]
    core/nodes/recommender.py에서 호출
"""

from database.neo4j_client import neo4j_client
from recommendation.queries import build_dual_constraint_query, LEVEL3_QUERY, BY_IDS_QUERY
from recommendation.scoring import post_process_candidates
from utils.logger import get_logger

logger = get_logger("RecommendationEngine")


class RecommendationEngine:
    """
    카테고리 필터 + 키워드 랭킹을 결합한 이중 제약 추천 엔진.

    모든 메서드는 @staticmethod로 구현되어 인스턴스 생성 없이 호출됩니다.
    Neo4j 쿼리 실행은 neo4j_client 싱글톤을 통해 수행됩니다.
    """

    @staticmethod
    def get_disliked_tags(session_id: str) -> list:
        """
        특정 세션의 사용자가 싫어한 태그 목록을 조회합니다.

        Args:
            session_id: 사용자 세션 ID

        Returns:
            태그명 문자열 리스트 (예: ["중식", "매운맛"])
        """
        query = """
        MATCH (u:User {session_id: $session_id})-[:DISLIKES]->(t:Tag)
        RETURN t.name AS tag
        """
        results = neo4j_client.run_query(query, {"session_id": session_id})
        return [r["tag"] for r in results]

    @staticmethod
    def _normalize_params(params: dict) -> dict:
        """
        쿼리 파라미터를 방어적으로 정제합니다.

        처리 내용:
            - 문자열: 앞뒤 공백 제거, 플레이스홀더("none", "null") → None 변환
            - 리스트: 각 요소 strip, 플레이스홀더 제거, 중복 제거
            - dict 리스트: 내부 value 필드도 동일하게 정제

        Args:
            params: 원본 파라미터 딕셔너리

        Returns:
            정제된 파라미터 딕셔너리 (새 객체)
        """
        normalized = {}
        for k, v in params.items():
            if isinstance(v, list):
                cleaned = []
                seen = set()
                for x in v:
                    if isinstance(x, str):
                        val = x.strip()
                        if (val.lower() not in ["", "none", "null", "..."]
                                and val not in seen):
                            cleaned.append(val)
                            seen.add(val)
                    elif isinstance(x, dict) and "value" in x:
                        val = str(x["value"]).strip()
                        if val.lower() not in ["", "none", "null", "..."]:
                            cleaned.append({**x, "value": val})
                    else:
                        cleaned.append(x)
                normalized[k] = cleaned
            elif isinstance(v, str):
                val = v.strip()
                if val.lower() in ["", "none", "null", "..."]:
                    normalized[k] = None
                else:
                    normalized[k] = val
            else:
                normalized[k] = v
        return normalized

    @staticmethod
    def recommend_dual_constraint(
        session_id: str,
        area_name: str,
        category_name: str,
        inferred_categories: list = None,
        keyword_intents: list = None,
        ranking_signals: list = None,
        viewed_ids: list = None,
        excluded_names: list = None,
        excluded_categories: list = None,
        negative_keywords: list = None,
        is_discovery: bool = False,
        diversity_flag: bool = False,
        limit: int = 10,
    ) -> list:
        """
        카테고리 필터 + 키워드 랭킹 이중 제약 추천을 수행합니다.

        [실행 흐름]
            1. 파라미터 정규화 (_normalize_params)
            2. Cypher 쿼리 조립 (queries.build_dual_constraint_query)
            3. Neo4j 실행 (neo4j_client.run_query)
            4. Python 후처리 (scoring.post_process_candidates)

        Args:
            session_id          : 사용자 세션 ID
            area_name           : 지역 필터 (None이면 전역)
            category_name       : 카테고리 필터 (None이면 미적용)
            inferred_categories : 추론된 카테고리 OR 조건 리스트
            keyword_intents     : 키워드 인텐트 (value + strength)
            ranking_signals     : 랭킹 부스트 시그널
            viewed_ids          : 제외할 기존 조회 ID
            excluded_names      : 제외할 식당명
            excluded_categories : 제외할 카테고리
            negative_keywords   : 부정 키워드
            is_discovery        : DISCOVERY 모드 여부 (임계값 완화)
            diversity_flag      : 카테고리 다양성 적용 여부
            limit               : 최대 반환 개수

        Returns:
            추천 결과 딕셔너리 리스트 (name, id, address, rating 등)
        """
        # ── 1. 파라미터 정규화 ──────
        params = RecommendationEngine._normalize_params({
            "session_id": session_id,
            "area_name": area_name,
            "category_name": category_name,
            "inferred_categories": inferred_categories or [],
            "keyword_intents": keyword_intents or [],
            "ranking_signals": ranking_signals or [],
            "viewed_ids": viewed_ids or [],
            "excluded_names": excluded_names or [],
            "excluded_categories": excluded_categories or [],
            "negative_keywords": negative_keywords or [],
            "is_discovery": is_discovery,
            "limit": limit,
        })

        keyword_intents_clean = params["keyword_intents"]
        keyword_values = [kw["value"] for kw in keyword_intents_clean]
        absolute_keywords = [
            kw["value"] for kw in keyword_intents_clean
            if kw.get("strength") == "ABSOLUTE"
        ]
        ranking_signals_clean = params["ranking_signals"]
        top_n_limit = limit * 3

        # ── 2. Cypher 쿼리 조립 ──────
        query = build_dual_constraint_query(
            params, keyword_values, absolute_keywords,
            ranking_signals_clean, top_n_limit,
        )

        # ── 3. Neo4j 실행 ──────
        candidates = neo4j_client.run_query(query, {
            "area_name": params["area_name"],
            "category_name": params["category_name"],
            "inferred_categories": params["inferred_categories"],
            "keyword_values": keyword_values,
            "ranking_signals": ranking_signals_clean,
            "absolute_keywords": absolute_keywords,
            "viewed_ids": params["viewed_ids"],
            "excluded_names": params["excluded_names"],
            "excluded_categories": params["excluded_categories"],
            "negative_keywords": params["negative_keywords"],
            "is_discovery": params["is_discovery"],
            "limit_n": top_n_limit,
        })

        # ── 4. Python 후처리 (다양성 + 중복제거 + 정렬) ──────
        return post_process_candidates(candidates, diversity_flag, limit)

    @staticmethod
    def recommend_level_3(
        session_id: str,
        area_name: str = None,
        viewed_ids: list = None,
        excluded_names: list = None,
        excluded_categories: list = None,
        limit: int = 5,
    ) -> list:
        """
        범위 확장형 기본 추천 (Level 3).
        키워드 없이 지역 + 평점 기반으로 추천합니다.

        Args:
            session_id          : 사용자 세션 ID
            area_name           : 지역 (None이면 전역)
            viewed_ids          : 제외할 기존 조회 ID
            excluded_names      : 제외할 식당명
            excluded_categories : 제외할 카테고리
            limit               : 최대 반환 개수

        Returns:
            추천 결과 딕셔너리 리스트
        """
        return neo4j_client.run_query(LEVEL3_QUERY, {
            "area_name": area_name,
            "viewed_ids": viewed_ids or [],
            "excluded_names": excluded_names or [],
            "excluded_categories": excluded_categories or [],
            "limit": limit,
        })

    @staticmethod
    def get_restaurants_by_ids(ids: list) -> list:
        """
        ID 리스트에 해당하는 식당 정보를 조회합니다.
        입력 순서를 보존하며 내부적으로 중복을 제거합니다.

        Args:
            ids: 식당 ID 리스트

        Returns:
            식당 정보 딕셔너리 리스트 (입력 순서 보존)
        """
        if not ids:
            return []

        # 순서 유지 중복 제거
        unique_ids = list(dict.fromkeys(ids))
        return neo4j_client.run_query(BY_IDS_QUERY, {"ids": unique_ids})

    @staticmethod
    def update_user_interaction(session_id: str, target_id: str,
                                interaction_type: str):
        """
        사용자의 식당 인터랙션(좋아요/싫어요)을 Neo4j에 기록합니다.

        좋아요 → INTERACTED 관계 (type: 'Like')
        싫어요 → DISLIKES 관계

        Args:
            session_id       : 사용자 세션 ID
            target_id        : 대상 식당 ID 또는 이름
            interaction_type : "Like" 또는 "Dislike"
        """
        if interaction_type == "Like":
            query = """
            MERGE (u:User {session_id: $session_id})
            WITH u
            MATCH (target) WHERE target.id = $target_id OR target.name = $target_id
            MERGE (u)-[:INTERACTED {type: 'Like'}]->(target)
            """
        else:
            query = """
            MERGE (u:User {session_id: $session_id})
            WITH u
            MATCH (target) WHERE target.id = $target_id OR target.name = $target_id
            MERGE (u)-[:DISLIKES]->(target)
            """
        neo4j_client.execute_write(
            query, {"session_id": session_id, "target_id": target_id}
        )
