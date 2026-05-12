import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any


NORMALIZATION_METHOD_RULE_SIMILARITY = "RULE_SIMILARITY"
MENU_STATUS_NORMALIZED = "NORMALIZED"
MENU_STATUS_REVIEW_CANDIDATE = "REVIEW_CANDIDATE"
MENU_STATUS_LOW_CONFIDENCE = "LOW_CONFIDENCE"

NORMALIZED_THRESHOLD = 0.88
REVIEW_CANDIDATE_THRESHOLD = 0.70

REMOVABLE_TOKENS = (
    "매콤",
    "직화",
    "수제",
    "프리미엄",
    "시그니처",
    "대표",
    "인기",
    "best",
    "BEST",
    "정식",
    "세트",
    "한상",
    "1인",
    "2인",
    "런치",
    "디너",
    "곱빼기",
    "대",
    "중",
    "소",
)

CANDIDATE_RULES = (
    (("제육",), "제육볶음"),
    (("김치", "찌개"), "김치찌개"),
    (("된장", "찌개"), "된장찌개"),
    (("크림", "파스타"), "크림파스타"),
    (("불고기", "덮밥"), "불고기덮밥"),
)


@dataclass(frozen=True)
class MenuNormalizationResult:
    raw_menu_name: str
    display_menu_name: str
    normalized_name: str | None
    canonical_name: str | None
    recipe_search_keyword: str | None
    menu_confidence: float
    menu_normalization_status: str
    normalization_method: str


class MenuNormalizer:
    def normalize(self, menu: dict[str, Any]) -> dict[str, Any]:
        raw_menu_name = self._raw_name(menu)
        result = self.normalize_name(raw_menu_name)

        return {
            **menu,
            "raw_menu_name": result.raw_menu_name,
            "display_menu_name": result.display_menu_name,
            "normalized_name": result.normalized_name,
            "canonical_name": result.canonical_name,
            "recipe_search_keyword": result.recipe_search_keyword,
            "menu_confidence": result.menu_confidence,
            "menu_normalization_status": result.menu_normalization_status,
            "normalization_method": result.normalization_method,
        }

    def normalize_name(self, raw_menu_name: str) -> MenuNormalizationResult:
        display_menu_name = raw_menu_name
        cleaned_name = clean_menu_text(raw_menu_name)
        candidate_name = build_candidate_name(cleaned_name)
        confidence = calculate_confidence(cleaned_name, candidate_name)
        status = determine_status(confidence)

        if status != MENU_STATUS_NORMALIZED:
            candidate_name = None

        return MenuNormalizationResult(
            raw_menu_name=raw_menu_name,
            display_menu_name=display_menu_name,
            normalized_name=candidate_name,
            canonical_name=candidate_name,
            recipe_search_keyword=candidate_name,
            menu_confidence=confidence,
            menu_normalization_status=status,
            normalization_method=NORMALIZATION_METHOD_RULE_SIMILARITY,
        )

    def _raw_name(self, menu: dict[str, Any]) -> str:
        for key in ("raw_menu_name", "name"):
            value = str(menu.get(key, "")).strip()
            if value:
                return value
        return ""


def clean_menu_text(raw_menu_name: str) -> str:
    cleaned = raw_menu_name
    for token in REMOVABLE_TOKENS:
        cleaned = cleaned.replace(token, " ")
    cleaned = re.sub(r"\d+", " ", cleaned)
    cleaned = re.sub(r"[^\w가-힣\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def build_candidate_name(cleaned_name: str) -> str | None:
    compact_name = cleaned_name.replace(" ", "")
    for keywords, candidate_name in CANDIDATE_RULES:
        if all(keyword in compact_name for keyword in keywords):
            return candidate_name
    return None


def calculate_confidence(cleaned_name: str, candidate_name: str | None) -> float:
    if not cleaned_name or candidate_name is None:
        return 0.0

    compact_name = cleaned_name.replace(" ", "")
    keyword_score = 1.0
    text_similarity_score = SequenceMatcher(None, compact_name, candidate_name).ratio()
    category_score = 1.0
    final_score = keyword_score * 0.5 + text_similarity_score * 0.3 + category_score * 0.2
    return round(final_score, 2)


def determine_status(confidence: float) -> str:
    if confidence >= NORMALIZED_THRESHOLD:
        return MENU_STATUS_NORMALIZED
    if confidence >= REVIEW_CANDIDATE_THRESHOLD:
        return MENU_STATUS_REVIEW_CANDIDATE
    return MENU_STATUS_LOW_CONFIDENCE
