"""
tests/test_parser_helpers.py — 파서 헬퍼 함수 단위 테스트

core/nodes/parser.py의 전처리 및 분류 헬퍼 함수를 검증합니다.
LLM 호출 없이 순수 로직만 테스트합니다.

실행: pytest tests/test_parser_helpers.py -v
"""

from core.nodes.parser import (
    normalize_area_text,
    validate_area_slot,
    sanitize_val,
    _classify_keywords,
)


class TestNormalizeAreaText:
    """지명 텍스트 정규화 테스트"""

    def test_remove_stop_words(self):
        """수식어 제거: '강남역 근처' → '강남'"""
        # '역'이 먼저 제거되고, 나머지 '강남'
        result = normalize_area_text("강남역")
        assert result == "강남구"  # 부분 일치 보정

    def test_partial_match_correction(self):
        """부분 일치 보정: '금천' → '금천구'"""
        assert normalize_area_text("금천") == "금천구"

    def test_none_input(self):
        """None 입력: None 반환"""
        assert normalize_area_text(None) is None
        assert normalize_area_text("") is None


class TestValidateAreaSlot:
    """지명 슬롯 검증 테스트"""

    def test_valid_area(self):
        """유효한 지역명: 그대로 통과"""
        area, kws = validate_area_slot("강남구", [])
        assert area == "강남구"

    def test_food_as_area(self):
        """음식 키워드가 area로 들어온 경우: null + keyword로 이동"""
        area, kws = validate_area_slot("파스타", [])
        assert area is None
        assert len(kws) > 0  # keyword로 재분류됨

    def test_null_placeholder(self):
        """플레이스홀더 값: null 처리"""
        area, kws = validate_area_slot("none", [])
        assert area is None

    def test_none_input(self):
        """None 입력: None 반환"""
        area, kws = validate_area_slot(None, [])
        assert area is None


class TestSanitizeVal:
    """값 정제 테스트"""

    def test_strip_whitespace(self):
        """앞뒤 공백 제거"""
        assert sanitize_val("  파스타  ") == "파스타"

    def test_placeholder_to_none(self):
        """플레이스홀더 → None"""
        assert sanitize_val("none") is None
        assert sanitize_val("null") is None
        assert sanitize_val("...") is None
        assert sanitize_val("") is None

    def test_non_string(self):
        """비문자열: 그대로 반환"""
        assert sanitize_val(42) == 42


class TestClassifyKeywords:
    """키워드 분류 테스트"""

    def test_hard_filter(self):
        """HARD_FILTER 분류"""
        kws = [{"value": "파스타", "type": "HARD_FILTER", "strength": "ABSOLUTE"}]
        result = _classify_keywords(kws)
        assert "파스타" in result["hard_filters"]
        assert "파스타" in result["positive_keywords"]

    def test_negative_keyword(self):
        """부정 키워드 분류"""
        kws = [{"value": "중식", "type": "HARD_FILTER", "is_negative": True}]
        result = _classify_keywords(kws)
        assert "중식" in result["excluded_categories"]

    def test_ranking_signal(self):
        """랭킹 시그널 분류"""
        kws = [{"value": "맛집", "type": "RANKING_SIGNAL"}]
        result = _classify_keywords(kws)
        # "맛집"은 DOMAIN_GENERIC_TERMS에 포함되어 필터링됨
        assert "맛집" not in result["ranking_signals"]

    def test_social_context_reclassification(self):
        """사회적 맥락 키워드 재분류: HARD_FILTER → SOFT_PREFERENCE"""
        kws = [{"value": "데이트", "type": "HARD_FILTER", "strength": "STRONG"}]
        result = _classify_keywords(kws)
        assert "데이트" in result["soft_preferences"]
        assert "데이트" not in result["hard_filters"]

    def test_generic_term_filtered(self):
        """도메인 일반 용어 필터링"""
        kws = [{"value": "식당", "type": "HARD_FILTER", "strength": "PREFERENCE"}]
        result = _classify_keywords(kws)
        assert "식당" not in result["hard_filters"]
