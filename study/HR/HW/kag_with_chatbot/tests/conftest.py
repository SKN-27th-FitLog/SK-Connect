"""
tests/conftest.py — pytest 공용 픽스처

모든 테스트 모듈이 공유하는 픽스처를 정의합니다.
"""

import pytest


@pytest.fixture
def sample_state():
    """
    테스트용 최소 AgentState 딕셔너리를 반환합니다.

    실제 LangGraph를 실행하지 않고 개별 함수를
    단위 테스트할 때 사용합니다.
    """
    return {
        "session_id": "test-session-001",
        "user_input": "강남역 맛집 추천해줘",
        "chat_history": [],
        "area": None,
        "category": None,
        "restaurant_name": None,
        "hard_filters": [],
        "soft_preferences": [],
        "ranking_signals": [],
        "keyword_strengths": {},
        "inferred_preferences": {},
        "ambiguous_goals": {},
        "positive_keywords": [],
        "keyword_intent": [],
        "excluded_categories": [],
        "excluded_names": [],
        "negative_keywords": [],
        "meta_intent": {
            "count": 5,
            "diversity_flag": False,
            "diversity_type": None,
            "ambiguity_score": 0.0,
            "intent_type": "recommend",
            "recall_anchor": None,
            "recall_scope": None,
        },
        "clarification_needed": False,
        "clarification_options": [],
        "clarification_answer": None,
        "search_mode": "FILTERED_SEARCH",
        "ui_mode": "SEARCH",
        "limit": 5,
        "recommendations": [],
        "viewed_ids": [],
        "current_level": 1,
        "feedback_type": None,
        "feedback_content": None,
        "target_id": None,
        "explanation": "",
        "relaxation_depth": 0,
        "rejection_log": [],
        "relaxation_history": [],
        "validation_report": [],
    }


@pytest.fixture
def sample_recommendations():
    """
    테스트용 추천 결과 리스트를 반환합니다.
    Validator, Generator 등의 테스트에 사용됩니다.
    """
    return [
        {
            "id": "r001", "name": "맛있는 파스타집",
            "category": "양식", "cat_group": "양식",
            "rating": 4.5, "quality_score": 0.85,
            "address": "서울시 강남구",
        },
        {
            "id": "r002", "name": "홍대 라멘하우스",
            "category": "일식", "cat_group": "일식",
            "rating": 4.2, "quality_score": 0.72,
            "address": "서울시 마포구",
        },
        {
            "id": "r003", "name": "종로 국밥",
            "category": "한식", "cat_group": "한식",
            "rating": 4.0, "quality_score": 0.65,
            "address": "서울시 종로구",
        },
    ]
