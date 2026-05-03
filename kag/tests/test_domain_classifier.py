from kag_graph.constants import Domain
from kag_graph.domain_classifier import DomainClassifier


def test_domain_classifier_detects_restaurant():
    result = DomainClassifier().classify("강남 맛집 추천해줘")

    assert result.value == Domain.RESTAURANT
    assert result.confidence >= 0.7


def test_domain_classifier_detects_it_news():
    result = DomainClassifier().classify("GPT 업데이트 알려줘")

    assert result.value == Domain.IT_NEWS
    assert result.confidence >= 0.7


def test_domain_classifier_detects_mixed():
    result = DomainClassifier().classify("판교 맛집이랑 판교 IT 뉴스 같이 보고 싶어")

    assert result.value == Domain.MIXED
    assert result.confidence >= 0.7


def test_domain_classifier_marks_unknown_for_ambiguous_text():
    result = DomainClassifier().classify("요즘 뭐가 좋아?")

    assert result.value == Domain.UNKNOWN
    assert result.needs_llm_assist is True
