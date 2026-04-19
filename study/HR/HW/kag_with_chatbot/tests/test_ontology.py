"""
tests/test_ontology.py — 온톨로지 계층 단위 테스트

knowledge/ontology.py의 매핑, 분류, 지명 검증 로직을 검증합니다.

실행: pytest tests/test_ontology.py -v
"""

from knowledge.ontology import OntologyLayer


class TestKeywordMapping:
    """KEYWORD_MAP 기반 키워드→카테고리 매핑 테스트"""

    def test_exact_match(self):
        """정확 일치: '파스타' → '양식'"""
        assert OntologyLayer.map_keyword("파스타") == "양식"

    def test_exact_match_japanese(self):
        """정확 일치: '라멘' → '일식'"""
        assert OntologyLayer.map_keyword("라멘") == "일식"

    def test_exact_match_korean(self):
        """정확 일치: '김치찌개' → '한식'"""
        assert OntologyLayer.map_keyword("김치찌개") == "한식"

    def test_synonym_match(self):
        """유의어 매핑: '면요리' → '면' → BROAD_INTENT"""
        # '면요리'는 KEYWORD_MAP에 없지만 SYNONYM_MAP으로 '면'으로 정규화
        # '면'도 KEYWORD_MAP에 없으므로 None 반환 (Broad Intent 전용)
        result = OntologyLayer.map_keyword("면요리")
        assert result is None  # KEYWORD_MAP에는 없음

    def test_unknown_keyword(self):
        """알 수 없는 키워드: None 반환"""
        assert OntologyLayer.map_keyword("xyz") is None

    def test_empty_keyword(self):
        """빈 입력: None 반환"""
        assert OntologyLayer.map_keyword("") is None
        assert OntologyLayer.map_keyword(None) is None


class TestBroadCategories:
    """BROAD_INTENT_MAP 기반 광의 의도 테스트"""

    def test_broad_noodle(self):
        """'면' → 5개 카테고리 후보"""
        cats = OntologyLayer.get_broad_categories("면")
        assert len(cats) >= 3
        assert "한식" in cats
        assert "일식" in cats

    def test_broad_meat(self):
        """'고기' → 3개 카테고리 후보"""
        cats = OntologyLayer.get_broad_categories("고기")
        assert "한식" in cats

    def test_synonym_broad(self):
        """유의어 경유: '면요리' → '면' → 광의 카테고리"""
        cats = OntologyLayer.get_broad_categories("면요리")
        assert len(cats) >= 3

    def test_no_broad(self):
        """광의 의도 아닌 키워드: 빈 리스트"""
        assert OntologyLayer.get_broad_categories("파스타") == []


class TestGeographicUnit:
    """지명 패턴 매칭 테스트"""

    def test_supported_area(self):
        """지원 지역명: True"""
        assert OntologyLayer.is_geographic_unit("강남") is True

    def test_administrative_pattern(self):
        """행정구역 패턴: True"""
        assert OntologyLayer.is_geographic_unit("금천구") is True
        assert OntologyLayer.is_geographic_unit("성수동") is True

    def test_non_geographic(self):
        """비지역 토큰: False"""
        assert OntologyLayer.is_geographic_unit("파스타") is False

    def test_empty_input(self):
        """빈 입력: False"""
        assert OntologyLayer.is_geographic_unit("") is False


class TestAdjacentCategories:
    """인접 카테고리 조회 테스트"""

    def test_western_adjacent(self):
        """양식 인접: 퓨전, 와인바 등"""
        adj = OntologyLayer.get_adjacent_categories("양식")
        assert "퓨전" in adj

    def test_unknown_category(self):
        """알 수 없는 카테고리: 빈 리스트"""
        assert OntologyLayer.get_adjacent_categories("xyz") == []
