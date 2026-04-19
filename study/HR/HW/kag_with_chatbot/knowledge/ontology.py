"""
knowledge/ontology.py — 음식 도메인 온톨로지 계층

키워드를 표준 카테고리로 매핑하고, 지명을 검증하며,
도메인 용어를 분류하는 시맨틱 지식 레이어입니다.

[포함 데이터셋]
- KEYWORD_MAP     : 메뉴/음식 → 대분류 카테고리 매핑 (파스타→양식)
- BROAD_INTENT_MAP: 광의 의도 → 후보 카테고리 목록 (면→[한식,일식,...])
- HYPONYM_MAP     : 상위어 → 하위어 확장 (면→[라멘,국수,...])
- SYNONYM_MAP     : 유의어 정규화 (면요리→면)
- RANKING_SIGNALS : 랭킹에 영향을 주는 시그널 (맛집, 유명한 등)
- DOMAIN_GENERIC_TERMS : 필터/점수에 영향 없는 일반 도메인 용어

[사용처]
- core/nodes/parser.py      : 키워드 분류 및 카테고리 매핑
- core/nodes/recommender.py : 온톨로지 확장 검색
- core/nodes/clarifier.py   : 광의 의도 감지
"""

import re
from typing import List, Optional


class OntologyLayer:
    """
    음식 도메인의 시맨틱 지식을 관리하는 온톨로지 클래스.

    주요 기능:
      1. 키워드 → 카테고리 매핑 (map_keyword)
      2. 광의 의도 후보 생성 (get_broad_categories)
      3. 인접 카테고리 조회 (get_adjacent_categories)
      4. 지명 검증 (is_geographic_unit)
    """

    # ─────────────────────────────────────────
    # 1. 키워드 → 카테고리 표준 매핑
    # ─────────────────────────────────────────
    # 사용자가 언급한 메뉴/음식명을 대분류 카테고리로 변환합니다.
    # 예: "파스타" → "양식", "라멘" → "일식"
    KEYWORD_MAP = {
        # 양식 계열
        "파스타": "양식", "피자": "양식", "스테이크": "양식",
        "리조또": "양식", "뇨끼": "양식", "라자냐": "양식",
        "감바스": "양식", "버거": "양식", "샌드위치": "양식",
        "와인바": "양식",
        # 일식 계열
        "라멘": "일식", "스시": "일식", "초밥": "일식",
        "돈까스": "일식", "소바": "일식", "우동": "일식",
        "텐동": "일식", "이자카야": "일식", "회": "일식",
        "사시미": "일식",
        # 한식 계열
        "김치찌개": "한식", "삼겹살": "한식", "국밥": "한식",
        "비빔밥": "한식", "불고기": "한식", "냉면": "한식",
        "갈비": "한식", "족발": "한식", "보쌈": "한식",
        "분식": "한식", "떡볶이": "한식",
        # 중식 계열
        "마라탕": "중식", "짜장면": "중식", "짬뽕": "중식",
        "딤섬": "중식", "양꼬치": "중식", "탕수욕": "중식",
        # 아시아 계열
        "쌀국수": "아시아음식", "팟타이": "아시아음식",
        "커리": "아시아음식", "인도카레": "아시아음식",
    }

    # ─────────────────────────────────────────
    # 1-1. 지명 관련 패턴 및 데이터
    # ─────────────────────────────────────────
    # 한국 행정구역 접미사 패턴 (구, 동, 역 등으로 끝나는 지명 매칭)
    GEOGRAPHIC_PATTERNS = r".+(구|동|읍|면|리|로|가|시|군|역)$"

    # 지명에서 제거할 수식어 (예: "강남역 근처" → "강남역" → "강남")
    STOP_WORDS_AREA = ["근처", "주변", "인근", "역"]

    # 시스템이 인식하는 주요 지역명 목록
    SUPPORTED_AREAS = [
        "강남", "홍대", "성수", "신촌", "건대",
        "금천", "구로", "종로", "마포", "서초",
    ]

    # ─────────────────────────────────────────
    # 1-2. 도메인 일반 용어 (필터/점수 영향 없음)
    # ─────────────────────────────────────────
    # "맛집 추천해줘"에서 "맛집"은 검색 필터가 아니라
    # 도메인 진입 신호(Domain Entry Marker)입니다.
    DOMAIN_GENERIC_TERMS = [
        "식당", "음식점", "맛집", "플레이스", "장소",
        "추천", "곳", "상황", "경우", "것", "데",
    ]

    # ─────────────────────────────────────────
    # 1-3. 랭킹 시그널 (결과 수에 영향 없이 점수만 조정)
    # ─────────────────────────────────────────
    # "맛집", "유명한" 등은 HARD_FILTER가 아니라
    # 기존 점수에 가중치(weight)를 곱하는 부스트 시그널입니다.
    RANKING_SIGNALS = {
        "평이 좋은": {"axis": "rating", "weight": 1.5},
        "인기 있는": {"axis": "popularity", "weight": 1.3},
        "무난한": {"axis": "stability", "weight": 1.2, "range": [3.5, 4.2]},
        "유명한": {"axis": "popularity", "weight": 1.4},
        "핫플": {"axis": "popularity", "weight": 1.4},
        "잘하는": {"axis": "rating", "weight": 1.3},
        "괜찮은": {"axis": "rating", "weight": 1.1},
        "가성비": {"axis": "value", "weight": 1.5},
    }

    # ─────────────────────────────────────────
    # 1-4. 광의 의도 → 후보 카테고리 (Broad Intent)
    # ─────────────────────────────────────────
    # "면 요리" 같은 상위 개념이 여러 카테고리에 걸칠 때
    # 후보 카테고리 목록을 반환합니다.
    BROAD_INTENT_MAP = {
        "면": ["한식", "일식", "양식", "아시아음식", "중식"],
        "고기": ["한식", "일식", "양식"],
        "해산물": ["한식", "일식", "아시아음식"],
        "디저트": ["카페", "베이커리"],
        "회": ["일식", "한식"],
    }

    # ─────────────────────────────────────────
    # 1-5. 하위어 확장 (Hyponym Expansion)
    # ─────────────────────────────────────────
    # 상위 개념(면)을 구체적 메뉴명으로 확장하여
    # 검색 범위를 넓힐 때 사용합니다.
    HYPONYM_MAP = {
        "면": ["라멘", "국수", "우동", "소바", "파스타", "짬뽕", "짜장면", "쌀국수", "냉면"],
        "고기": ["삼겹살", "스테이크", "갈비", "불고기", "족발"],
        "회": ["사시미", "스시", "초밥"],
    }

    # ─────────────────────────────────────────
    # 1-6. 유의어 정규화 테이블
    # ─────────────────────────────────────────
    # 사용자가 다양한 표현을 사용해도
    # 내부적으로 하나의 표준 키워드로 통일합니다.
    SYNONYM_MAP = {
        "면요리": "면", "국수": "면", "누들": "면", "면류": "면", "면 요리": "면",
        "고기집": "고기", "고기요리": "고기",
        "디저트까페": "디저트", "회집": "회",
        "일식집": "일식", "중국집": "중식", "한식당": "한식", "양식당": "양식",
    }

    # ─────────────────────────────────────────
    # 1-7. 인접 카테고리 (완화 시 확장 후보)
    # ─────────────────────────────────────────
    # 검색 결과가 부족할 때 EXPAND_CATEGORY 완화에서
    # 현재 카테고리와 유사한 카테고리로 확장합니다.
    ADJACENCY_MAP = {
        "양식": ["퓨전", "와인바", "이탈리안", "프렌치"],
        "한식": ["분식", "육류", "찜/탕"],
        "일식": ["아시아음식", "술집"],
        "중식": ["아시아음식", "퓨전"],
        "아시아음식": ["중식", "일식"],
    }

    # 레거시 호환용 (RANKING_SIGNALS + "맛집" 항목)
    GENERIC_SIGNALS = {**RANKING_SIGNALS, "맛집": {"axis": "rating", "weight": 1.0}}

    # ═════════════════════════════════════════
    # 메서드
    # ═════════════════════════════════════════

    @classmethod
    def is_geographic_unit(cls, text: str) -> bool:
        """
        주어진 텍스트가 행정구역 패턴이거나 지원되는 지역명인지 확인합니다.

        Args:
            text: 검증할 지명 텍스트

        Returns:
            True = 지리적 단위로 인정, False = 비지역 토큰

        판단 기준:
            1. SUPPORTED_AREAS 목록에 정확히 일치하는 경우 (예: "강남")
            2. 행정구역 접미사 패턴에 매칭되는 경우 (예: "금천구", "성수동")
        """
        if not text:
            return False
        if any(area == text for area in cls.SUPPORTED_AREAS):
            return True
        return bool(re.match(cls.GEOGRAPHIC_PATTERNS, text))

    @classmethod
    def map_keyword(cls, keyword: str) -> Optional[str]:
        """
        음식 키워드를 대분류 카테고리로 매핑합니다.

        Args:
            keyword: 매핑할 음식/메뉴 키워드 (예: "파스타")

        Returns:
            매핑된 카테고리명 (예: "양식") 또는 None (매핑 실패)

        매핑 순서 (Multi-stage Lookup):
            1단계: KEYWORD_MAP에서 정확(exact) 일치 검색
            2단계: SYNONYM_MAP으로 유의어 정규화 후 재검색
            3단계: 2글자 이상인 경우 부분 매칭 (startswith)
        """
        if not keyword:
            return None

        # 1단계: 정확 일치
        if keyword in cls.KEYWORD_MAP:
            return cls.KEYWORD_MAP[keyword]

        # 2단계: 유의어 정규화 후 재검색
        normalized = cls.SYNONYM_MAP.get(keyword, keyword)
        if normalized in cls.KEYWORD_MAP:
            return cls.KEYWORD_MAP[normalized]

        # 3단계: 부분 매칭 (1글자 키워드는 오매칭 방지를 위해 제외)
        if len(keyword) > 1:
            for key, cat in cls.KEYWORD_MAP.items():
                if key == keyword or key.startswith(keyword):
                    return cat

        return None

    @classmethod
    def get_broad_categories(cls, keyword: str) -> List[str]:
        """
        광의 의도 키워드에 해당하는 후보 카테고리 목록을 반환합니다.

        예: "면" → ["한식", "일식", "양식", "아시아음식", "중식"]
        예: "고기" → ["한식", "일식", "양식"]

        Args:
            keyword: 확인할 키워드

        Returns:
            후보 카테고리 리스트 (해당하지 않으면 빈 리스트)

        조회 순서:
            1. BROAD_INTENT_MAP 정확 일치
            2. SYNONYM_MAP 정규화 후 재조회
            3. 부분 문자열 매칭 (짧은 키워드 대상)
        """
        if not keyword:
            return []

        # 1단계: 정확 일치
        if keyword in cls.BROAD_INTENT_MAP:
            return cls.BROAD_INTENT_MAP[keyword]

        # 2단계: 유의어 정규화
        normalized = cls.SYNONYM_MAP.get(keyword, keyword)
        if normalized in cls.BROAD_INTENT_MAP:
            return cls.BROAD_INTENT_MAP[normalized]

        # 3단계: 부분 매칭 (예: "면요리맛집" → "면")
        for key, cats in cls.BROAD_INTENT_MAP.items():
            if key in keyword:
                return cats

        return []

    @classmethod
    def get_adjacent_categories(cls, category: str) -> List[str]:
        """
        주어진 카테고리의 인접(유사) 카테고리 목록을 반환합니다.
        EXPAND_CATEGORY 완화 전략에서 검색 범위를 넓힐 때 사용합니다.

        Args:
            category: 현재 카테고리 (예: "양식")

        Returns:
            인접 카테고리 리스트 (예: ["퓨전", "와인바", "이탈리안", "프렌치"])
        """
        return cls.ADJACENCY_MAP.get(category, [])
