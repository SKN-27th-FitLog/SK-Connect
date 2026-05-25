import json
from pathlib import Path

from kag_graph.it_news_importer import build_keyword_extraction_statements


def test_build_keyword_extraction_statements_maps_jsonl_to_news_graph(tmp_path: Path):
    jsonl_file = tmp_path / "keyword_extraction.jsonl"
    record = {
        "article_id": "a1",
        "source": "geeknews",
        "category_cd": "IC02",
        "title": "OpenAI GPT 출시",
        "url": "https://example.com/a1",
        "published_at": "2026-05-13T09:00:00+09:00",
        "content_hash": "hash",
        "event_signals": [{"action_type": "RELEASE", "matched_text": "출시", "confidence": 0.8, "source": "morph_action_dictionary"}],
        "keywords": [
            {
                "canonical_name": "GPT-5",
                "matched_keyword": "GPT",
                "node_type": "Technology",
                "importance_score": 0.8,
                "classification_confidence": 0.9,
                "source": "llm",
            },
            {
                "canonical_name": "OpenAI",
                "matched_keyword": "OpenAI",
                "node_type": "Company",
                "importance_score": 0.9,
                "classification_confidence": 1.0,
                "source": "dictionary",
            },
            {
                "canonical_name": "출시",
                "matched_keyword": "출시",
                "node_type": "Event",
                "importance_score": 0.6,
                "classification_confidence": 0.8,
                "source": "llm",
            },
            {
                "canonical_name": "AI",
                "matched_keyword": "AI",
                "node_type": "Topic",
                "importance_score": 0.7,
                "classification_confidence": 0.8,
                "source": "llm",
            },
        ],
    }
    jsonl_file.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")

    statements = build_keyword_extraction_statements(jsonl_file)

    assert [statement.name for statement in statements] == [
        "news_article:a1",
        "news_keyword:a1:Technology:GPT-5",
        "news_keyword:a1:Company:OpenAI",
        "news_keyword:a1:Event:출시",
        "news_keyword:a1:Topic:AI",
    ]
    assert "event_signals" in statements[0].cypher
    assert statements[0].params["event_signals"] == json.dumps(record["event_signals"], ensure_ascii=False)
    assert "MERGE (node:Technology {canonical_name: $canonical_name})" in statements[1].cypher
    assert "MENTIONS_TECHNOLOGY" in statements[1].cypher
    assert "MENTIONS_COMPANY" in statements[2].cypher
    assert "MENTIONS_EVENT" in statements[3].cypher
    assert "HAS_TOPIC" in statements[4].cypher
