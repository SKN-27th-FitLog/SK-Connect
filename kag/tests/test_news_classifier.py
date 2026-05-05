from kag_graph.news_classifier import NewsClassifier


def test_news_classifier_extracts_documented_news_entities():
    result = NewsClassifier().classify(
        title="OpenAI GPT update improves cloud security",
        content="Microsoft also mentioned Kubernetes support.",
    )

    assert [term.normalized_name for term in result.technologies] == ["gpt", "kubernetes"]
    assert [term.normalized_name for term in result.companies] == ["openai", "microsoft"]
    assert [term.normalized_name for term in result.events] == ["update"]
    assert [term.normalized_name for term in result.topics] == ["cloud", "security"]


def test_news_classifier_returns_empty_groups_without_known_keywords():
    result = NewsClassifier().classify(
        title="Personal essay about development habits",
        content="No configured graph condition appears here.",
    )

    assert result.technologies == []
    assert result.companies == []
    assert result.events == []
    assert result.topics == []
