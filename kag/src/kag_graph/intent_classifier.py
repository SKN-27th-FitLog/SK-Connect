from kag_graph.constants import Domain, Intent
from kag_graph.models import ClassificationResult


class IntentClassifier:
    def classify(self, raw_text: str, domain: str) -> ClassificationResult:
        if domain == Domain.MIXED and "같이" in raw_text:
            return ClassificationResult(Intent.CONCEPT_BRIDGE_SEARCH, 0.85, "mixed concept bridge request")

        if domain == Domain.RESTAURANT:
            if any(token in raw_text for token in ("싫어", "싫은", "말고", "제외", "빼줘", "안 들어간", "피하고 싶어")):
                return ClassificationResult(Intent.RESTAURANT_EXCLUSION_SEARCH, 0.9, "negative restaurant condition")
            if any(token in raw_text for token in ("1만원", "2만원", "저렴한", "가격", "가성비")):
                return ClassificationResult(Intent.RESTAURANT_PRICE_FILTER, 0.85, "restaurant price condition")
            return ClassificationResult(Intent.RESTAURANT_RECOMMENDATION, 0.75, "default restaurant recommendation")

        if domain == Domain.IT_NEWS:
            if any(token in raw_text for token in ("비교", "vs", "경쟁", "차이")):
                return ClassificationResult(Intent.NEWS_COMPARISON, 0.85, "news comparison expression")
            if any(token in raw_text for token in ("업데이트", "사고", "규제", "투자", "출시")):
                return ClassificationResult(Intent.NEWS_EVENT_SEARCH, 0.85, "news event expression")
            return ClassificationResult(Intent.NEWS_SUMMARY, 0.75, "default news summary")

        return ClassificationResult(Intent.CLARIFICATION_REQUIRED, 0.0, "unsupported or unknown domain", needs_llm_assist=True)
