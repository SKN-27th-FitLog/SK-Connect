from kag_graph.constants import Domain
from kag_graph.models import ClassificationResult


class DomainClassifier:
    RESTAURANT_KEYWORDS = {"맛집", "식당", "중국집", "카페", "밥집", "메뉴", "음식", "회식", "혼밥", "배달", "가격", "강남", "홍대"}
    IT_NEWS_KEYWORDS = {"뉴스", "기사", "GPT", "AI", "클라우드", "보안", "업데이트", "투자", "규제", "삼성", "애플", "OpenAI", "Microsoft", "Google"}

    def classify(self, raw_text: str) -> ClassificationResult:
        restaurant_score = self._keyword_score(raw_text, self.RESTAURANT_KEYWORDS)
        news_score = self._keyword_score(raw_text, self.IT_NEWS_KEYWORDS)

        if restaurant_score > 0 and news_score > 0:
            return ClassificationResult(Domain.MIXED, 0.85, "restaurant and it_news keywords matched")

        if restaurant_score > 0:
            return ClassificationResult(Domain.RESTAURANT, 0.8, "restaurant keywords matched")

        if news_score > 0:
            return ClassificationResult(Domain.IT_NEWS, 0.8, "it_news keywords matched")

        return ClassificationResult(Domain.UNKNOWN, 0.0, "no domain keyword matched", needs_llm_assist=True)

    def _keyword_score(self, raw_text: str, keywords: set[str]) -> int:
        return sum(1 for keyword in keywords if keyword in raw_text)
