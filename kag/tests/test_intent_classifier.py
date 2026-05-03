from kag_graph.constants import Domain, Intent
from kag_graph.intent_classifier import IntentClassifier


def test_intent_classifier_detects_restaurant_exclusion():
    result = IntentClassifier().classify("면은 싫은데 중국집 가고 싶어", Domain.RESTAURANT)

    assert result.value == Intent.RESTAURANT_EXCLUSION_SEARCH


def test_intent_classifier_detects_price_filter():
    result = IntentClassifier().classify("1만원 이하 한식집 알려줘", Domain.RESTAURANT)

    assert result.value == Intent.RESTAURANT_PRICE_FILTER


def test_intent_classifier_detects_news_event():
    result = IntentClassifier().classify("GPT 업데이트 알려줘", Domain.IT_NEWS)

    assert result.value == Intent.NEWS_EVENT_SEARCH


def test_intent_classifier_detects_news_comparison():
    result = IntentClassifier().classify("삼성과 애플 비교해줘", Domain.IT_NEWS)

    assert result.value == Intent.NEWS_COMPARISON
