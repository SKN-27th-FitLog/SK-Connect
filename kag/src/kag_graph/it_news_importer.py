from __future__ import annotations

import json
from pathlib import Path

from kag_graph.hive_importer import GraphWriteStatement


NEWS_ARTICLE_FROM_KEYWORD_EXTRACTION_CYPHER = """
MERGE (article:NewsArticle {article_id: $article_id})
SET article.title = $title,
    article.url = $url,
    article.source = $source,
    article.category_cd = $category_cd,
    article.published_at = datetime($published_at),
    article.content_hash = $content_hash,
    article.event_signals = $event_signals
"""


KEYWORD_NODE_CYPHER_BY_TYPE = {
    "Technology": """
MATCH (article:NewsArticle {article_id: $article_id})
MERGE (node:Technology {canonical_name: $canonical_name})
SET node.name = $canonical_name
MERGE (article)-[r:MENTIONS_TECHNOLOGY]->(node)
SET r.matched_keyword = $matched_keyword,
    r.importance_score = $importance_score,
    r.classification_confidence = $classification_confidence,
    r.source = $source
""",
    "Company": """
MATCH (article:NewsArticle {article_id: $article_id})
MERGE (node:Company {canonical_name: $canonical_name})
SET node.name = $canonical_name
MERGE (article)-[r:MENTIONS_COMPANY]->(node)
SET r.matched_keyword = $matched_keyword,
    r.importance_score = $importance_score,
    r.classification_confidence = $classification_confidence,
    r.source = $source
""",
    "Event": """
MATCH (article:NewsArticle {article_id: $article_id})
MERGE (node:Event {canonical_name: $canonical_name})
SET node.name = $canonical_name
MERGE (article)-[r:MENTIONS_EVENT]->(node)
SET r.matched_keyword = $matched_keyword,
    r.importance_score = $importance_score,
    r.classification_confidence = $classification_confidence,
    r.source = $source
""",
    "Topic": """
MATCH (article:NewsArticle {article_id: $article_id})
MERGE (node:Topic {canonical_name: $canonical_name})
SET node.name = $canonical_name
MERGE (article)-[r:HAS_TOPIC]->(node)
SET r.matched_keyword = $matched_keyword,
    r.importance_score = $importance_score,
    r.classification_confidence = $classification_confidence,
    r.source = $source
""",
}


def build_keyword_extraction_statements(jsonl_file: Path) -> list[GraphWriteStatement]:
    statements: list[GraphWriteStatement] = []
    with jsonl_file.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            record = json.loads(line)
            statements.append(_build_article_statement(record))
            statements.extend(_build_keyword_statements(record))
    return statements


def _build_article_statement(record: dict) -> GraphWriteStatement:
    article_id = str(record["article_id"]).strip()
    return GraphWriteStatement(
        name=f"news_article:{article_id}",
        cypher=NEWS_ARTICLE_FROM_KEYWORD_EXTRACTION_CYPHER,
        params={
            "article_id": article_id,
            "title": record.get("title", ""),
            "url": record.get("url", ""),
            "source": record.get("source", ""),
            "category_cd": record.get("category_cd", ""),
            "published_at": record.get("published_at") or "1970-01-01T00:00:00+00:00",
            "content_hash": record.get("content_hash", ""),
            "event_signals": json.dumps(record.get("event_signals", []), ensure_ascii=False),
        },
    )


def _build_keyword_statements(record: dict) -> list[GraphWriteStatement]:
    article_id = str(record["article_id"]).strip()
    statements: list[GraphWriteStatement] = []
    for keyword in record.get("keywords", []):
        node_type = str(keyword.get("node_type", "")).strip()
        cypher = KEYWORD_NODE_CYPHER_BY_TYPE.get(node_type)
        if cypher is None:
            continue
        canonical_name = str(keyword["canonical_name"]).strip()
        statements.append(
            GraphWriteStatement(
                name=f"news_keyword:{article_id}:{node_type}:{canonical_name}",
                cypher=cypher,
                params={
                    "article_id": article_id,
                    "canonical_name": canonical_name,
                    "matched_keyword": keyword.get("matched_keyword", ""),
                    "importance_score": float(keyword.get("importance_score", 0.0)),
                    "classification_confidence": float(keyword.get("classification_confidence", 0.0)),
                    "source": keyword.get("source", ""),
                },
            )
        )
    return statements
