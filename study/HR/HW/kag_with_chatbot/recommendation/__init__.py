# ──────────────────────────────────────────────
# recommendation 패키지
# ──────────────────────────────────────────────
# 맛집 추천 엔진의 핵심 로직을 포함합니다.
#   - engine.py   : RecommendationEngine 메인 클래스
#   - queries.py  : Cypher 쿼리 빌더 (Neo4j 전용)
#   - scoring.py  : 스코어링, 다양성 보정, 중복 제거 로직
# ──────────────────────────────────────────────
from recommendation.engines import RecommendationEngine

__all__ = ["RecommendationEngine"]
