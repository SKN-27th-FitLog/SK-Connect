"""
키워드 정규화 사전 (Hierarchical merge).

Layer 1 (동의어 -> 정규형 canonical):
    형태소 시그니처(맛있다, 좋다, 친절하다 등)를 의미 단위 토큰으로 매핑한다.
    예) 맛있다, 맛나다, 맛이좋다 -> TASTE_POS

Layer 2 (정규형 -> 카테고리):
    정규형 토큰을 상위 카테고리(맛, 가성비, 서비스, 분위기, 양 등)로 묶는다.

select_shop._group_similar_keywords()에서 이 모듈을 사용해
형태소 시그니처가 다르더라도 같은 의미면 한 그룹으로 묶이게 한다.
"""
from __future__ import annotations

# =========================================================
# Layer 1: 술어/행동 -> 정규형
# =========================================================
# key는 _extract_keyword_signatures / _extract_keyword_actions가
# 만드는 형태(어간 + "다") 그대로 적는다.
PREDICATE_SYNONYMS: dict[str, str] = {
    # 맛 - 긍정
    "맛있다": "TASTE_POS",
    "맛나다": "TASTE_POS",
    "맛좋다": "TASTE_POS",
    "맛이좋다": "TASTE_POS",
    "환상적이다": "TASTE_POS",
    "일품이다": "TASTE_POS",
    "별미다": "TASTE_POS",
    # 맛 - 부정
    "맛없다": "TASTE_NEG",
    "별로이다": "TASTE_NEG",
    "별로다": "TASTE_NEG",
    "느끼하다": "TASTE_HEAVY",
    "짜다": "TASTE_SALTY",
    "싱겁다": "TASTE_BLAND",
    # 맛 - 특성
    "담백하다": "TASTE_LIGHT",
    "고소하다": "TASTE_RICH",
    "달다": "TASTE_SWEET",
    "달콤하다": "TASTE_SWEET",
    "매콤하다": "TASTE_SPICY",
    "매콤달콤하다": "TASTE_SPICY",
    "얼큰하다": "TASTE_SPICY",
    "칼칼하다": "TASTE_SPICY",
    "시원하다": "TASTE_REFRESH",
    "쫄깃하다": "TEXTURE_CHEWY",
    "바삭하다": "TEXTURE_CRISP",
    "부드럽다": "TEXTURE_SOFT",
    "촉촉하다": "TEXTURE_MOIST",
    "편하다": "EASE_POS",
    "간편하다": "EASE_POS",
    # 가격/가성비
    "저렴하다": "PRICE_GOOD",
    "싸다": "PRICE_GOOD",
    "가성비있다": "PRICE_GOOD",
    "가성비좋다": "PRICE_GOOD",
    "착하다": "PRICE_GOOD",  # "가격이 착하다"
    "비싸다": "PRICE_BAD",
    # 친절/서비스
    "친절하다": "SERVICE_POS",
    "상냥하다": "SERVICE_POS",
    "정겹다": "SERVICE_POS",
    "정성스럽다": "SERVICE_POS",
    "불친절하다": "SERVICE_NEG",
    "무뚝뚝하다": "SERVICE_NEG",
    "빠르다": "SERVICE_FAST",
    "신속하다": "SERVICE_FAST",
    "느리다": "SERVICE_SLOW",
    # 분위기/위생
    "깔끔하다": "AMBIENCE_CLEAN",
    "청결하다": "AMBIENCE_CLEAN",
    "깨끗하다": "AMBIENCE_CLEAN",
    "더럽다": "AMBIENCE_DIRTY",
    "지저분하다": "AMBIENCE_DIRTY",
    "조용하다": "AMBIENCE_QUIET",
    "시끄럽다": "AMBIENCE_NOISY",
    "아늑하다": "AMBIENCE_COZY",
    "편안하다": "AMBIENCE_COZY",
    "아담하다": "AMBIENCE_COZY",
    "넓다": "AMBIENCE_SPACIOUS",
    "쾌적하다": "AMBIENCE_CLEAN",
    "좁다": "AMBIENCE_NARROW",
    "감성있다": "AMBIENCE_POS",
    # 양/포션
    "많다": "PORTION_LARGE",
    "푸짐하다": "PORTION_LARGE",
    "넉넉하다": "PORTION_LARGE",
    "푸근하다": "PORTION_LARGE",
    "적다": "PORTION_SMALL",
    "부족하다": "PORTION_SMALL",
    # 분위기 일반
    "서민적이다": "AMBIENCE_HOMELY",
}

# =========================================================
# 명사 + 술어 결합으로만 의미가 결정되는 케이스
# (단일 술어로는 모호한 "좋다/있다/없다"는 명사 컨텍스트가 필요하다)
# =========================================================
NOUN_PREDICATE_COMBOS: dict[tuple[str, str], str] = {
    # 맛
    ("맛", "좋다"): "TASTE_POS",
    ("맛", "있다"): "TASTE_POS",
    ("맛", "최고다"): "TASTE_POS",
    ("맛", "일품이다"): "TASTE_POS",
    ("맛", "없다"): "TASTE_NEG",
    ("맛", "별로이다"): "TASTE_NEG",
    ("맛", "별로다"): "TASTE_NEG",
    # 가격/가성비
    ("가격", "좋다"): "PRICE_GOOD",
    ("가격", "착하다"): "PRICE_GOOD",
    ("가격", "저렴하다"): "PRICE_GOOD",
    ("가격", "싸다"): "PRICE_GOOD",
    ("가격", "비싸다"): "PRICE_BAD",
    ("가성비", "좋다"): "PRICE_GOOD",
    ("가성비", "있다"): "PRICE_GOOD",
    # 서비스
    ("서비스", "좋다"): "SERVICE_POS",
    ("서비스", "친절하다"): "SERVICE_POS",
    ("응대", "좋다"): "SERVICE_POS",
    ("응대", "친절하다"): "SERVICE_POS",
    ("사장", "친절하다"): "SERVICE_POS",
    ("사장님", "친절하다"): "SERVICE_POS",
    ("주인", "친절하다"): "SERVICE_POS",
    ("직원", "친절하다"): "SERVICE_POS",
    ("점원", "친절하다"): "SERVICE_POS",
    # 분위기
    ("분위기", "좋다"): "AMBIENCE_POS",
    ("인테리어", "좋다"): "AMBIENCE_POS",
    ("매장", "깔끔하다"): "AMBIENCE_CLEAN",
    ("매장", "깨끗하다"): "AMBIENCE_CLEAN",
    ("매장", "넓다"): "AMBIENCE_SPACIOUS",
    # 양
    ("양", "많다"): "PORTION_LARGE",
    ("양", "푸짐하다"): "PORTION_LARGE",
    ("양", "넉넉하다"): "PORTION_LARGE",
    ("양", "적다"): "PORTION_SMALL",
    ("양", "부족하다"): "PORTION_SMALL",
}

# =========================================================
# Layer 2: 정규형 -> 상위 카테고리
# =========================================================
CANONICAL_CATEGORIES: dict[str, str] = {
    # 맛 카테고리
    "TASTE_POS": "맛",
    "TASTE_NEG": "맛",
    "TASTE_HEAVY": "맛",
    "TASTE_SALTY": "맛",
    "TASTE_BLAND": "맛",
    "TASTE_LIGHT": "맛",
    "TASTE_RICH": "맛",
    "TASTE_SWEET": "맛",
    "TASTE_SPICY": "맛",
    "TASTE_REFRESH": "맛",
    "TEXTURE_CHEWY": "맛",
    "TEXTURE_CRISP": "맛",
    "TEXTURE_SOFT": "맛",
    "TEXTURE_MOIST": "맛",
    # 가성비 카테고리
    "PRICE_GOOD": "가성비",
    "PRICE_BAD": "가성비",
    # 서비스 카테고리
    "SERVICE_POS": "서비스",
    "SERVICE_NEG": "서비스",
    "SERVICE_FAST": "서비스",
    "SERVICE_SLOW": "서비스",
    # 분위기 카테고리
    "AMBIENCE_POS": "분위기",
    "AMBIENCE_CLEAN": "분위기",
    "AMBIENCE_DIRTY": "분위기",
    "AMBIENCE_QUIET": "분위기",
    "AMBIENCE_NOISY": "분위기",
    "AMBIENCE_COZY": "분위기",
    "AMBIENCE_SPACIOUS": "분위기",
    "AMBIENCE_NARROW": "분위기",
    "AMBIENCE_HOMELY": "분위기",
    # 양 카테고리
    "PORTION_LARGE": "양",
    "PORTION_SMALL": "양",
    # 기타 - 사용 편의성
    "EASE_POS": "기타",
}

# 명사 단독으로도 카테고리 힌트가 되는 어휘
# (술어가 평범한 "좋다/있다"여도 명사로 카테고리를 잡는다)
NOUN_CATEGORY_HINTS: dict[str, str] = {
    "맛": "맛",
    "풍미": "맛",
    "향": "맛",
    "식감": "맛",
    "가격": "가성비",
    "가성비": "가성비",
    "값": "가성비",
    "서비스": "서비스",
    "응대": "서비스",
    "사장": "서비스",
    "사장님": "서비스",
    "주인": "서비스",
    "직원": "서비스",
    "점원": "서비스",
    "분위기": "분위기",
    "인테리어": "분위기",
    "매장": "분위기",
    "공간": "분위기",
    "내부": "분위기",
    "양": "양",
    "포션": "양",
}


# =========================================================
# 공개 함수
# =========================================================
def _normalize_predicate_form(form: str) -> str:
    """'맛있'처럼 어간만 들어와도 '맛있다'로 맞춰 사전 조회한다."""
    text = (form or "").strip()
    if not text:
        return ""
    return text if text.endswith("다") else f"{text}다"


def canonicalize_signals(
    predicates: set[str],
    actions: set[str],
    nouns: set[str],
) -> set[str]:
    """형태소 신호로부터 정규형 토큰 집합을 만든다.

    매핑 순서:
        1) 'N_V다' 형태(_extract_keyword_signatures가 만드는 일반 술어)는
           명사부와 술어부를 분리해 NOUN_PREDICATE_COMBOS로 먼저 시도.
        2) 단일 술어/액션은 PREDICATE_SYNONYMS로 매핑.
        3) (명사, 술어) 페어를 모든 조합으로 NOUN_PREDICATE_COMBOS 시도.
    """
    canonical: set[str] = set()

    raw_signals = set(predicates) | set(actions)

    for signal in raw_signals:
        text = (signal or "").strip()
        if not text:
            continue
        # '맛_좋다'처럼 명사_술어 결합 시그니처
        if "_" in text:
            noun_part, predicate_part = text.split("_", 1)
            key = (noun_part, _normalize_predicate_form(predicate_part))
            if key in NOUN_PREDICATE_COMBOS:
                canonical.add(NOUN_PREDICATE_COMBOS[key])
                continue
        # 단일 술어/액션
        if text in PREDICATE_SYNONYMS:
            canonical.add(PREDICATE_SYNONYMS[text])

    # 명사 + 술어 결합 시도 (시그니처가 분리돼 있을 때 대비)
    normalized_predicates = {
        _normalize_predicate_form(predicate)
        for predicate in raw_signals
        if predicate
    }
    for noun in nouns:
        noun_text = (noun or "").strip()
        if not noun_text:
            continue
        for predicate in normalized_predicates:
            key = (noun_text, predicate)
            if key in NOUN_PREDICATE_COMBOS:
                canonical.add(NOUN_PREDICATE_COMBOS[key])

    return canonical


def category_of_canonical(canonical: str) -> str | None:
    """정규형 토큰의 상위 카테고리(맛/가성비/서비스/분위기/양 등)를 반환한다."""
    return CANONICAL_CATEGORIES.get(canonical)


def categories_of_keyword(
    canonical_signals_set: set[str],
    nouns: set[str],
) -> set[str]:
    """키워드 하나가 속할 수 있는 상위 카테고리 집합을 모은다.

    정규형 매핑이 있으면 거기서 카테고리를 우선 가져오고,
    매핑이 없으면 명사 힌트(NOUN_CATEGORY_HINTS)로 백업한다.
    """
    categories: set[str] = set()
    for canonical in canonical_signals_set:
        category = CANONICAL_CATEGORIES.get(canonical)
        if category:
            categories.add(category)
    if not categories:
        for noun in nouns:
            category = NOUN_CATEGORY_HINTS.get((noun or "").strip())
            if category:
                categories.add(category)
    return categories


def primary_category(
    canonical_signals_set: set[str],
    nouns: set[str],
) -> str | None:
    """대표 카테고리(있을 경우)를 하나 반환한다."""
    categories = categories_of_keyword(canonical_signals_set, nouns)
    if not categories:
        return None
    # 우선순위: 맛 > 가성비 > 서비스 > 분위기 > 양 > 그 외
    priority = ["맛", "가성비", "서비스", "분위기", "양"]
    for category in priority:
        if category in categories:
            return category
    return next(iter(sorted(categories)))
