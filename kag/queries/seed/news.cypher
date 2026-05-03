MERGE (gpt:Technology {normalized_name: "gpt"})
SET gpt.technology_id = "TECH001", gpt.name = "GPT", gpt.technology_type = "ai_model";

MERGE (cloud:Technology {normalized_name: "클라우드"})
SET cloud.technology_id = "TECH002", cloud.name = "클라우드", cloud.technology_type = "infra";

MERGE (update_event:Event {normalized_name: "업데이트"})
SET update_event.event_id = "EVENT001", update_event.name = "업데이트", update_event.event_type = "release";

MERGE (investment_event:Event {normalized_name: "투자회복"})
SET investment_event.event_id = "EVENT002", investment_event.name = "투자회복", investment_event.event_type = "market";

MERGE (openai:Company {normalized_name: "openai"})
SET openai.company_id = "COMP001", openai.name = "OpenAI", openai.company_type = "ai", openai.country = "US";

MERGE (article:NewsArticle {article_id: "A001"})
SET article.title = "GPT 업데이트 공개",
    article.summary = "새 GPT 업데이트가 개발자 기능과 응답 품질을 개선했다.",
    article.published_at = date("2026-05-01"),
    article.source = "sample",
    article.url = "https://example.com/news/a001",
    article.importance_score = 0.9;

MERGE (pangyo_article:NewsArticle {article_id: "A006"})
SET pangyo_article.title = "판교 IT 기업 투자회복",
    pangyo_article.summary = "판교 IT 기업의 투자 심리가 회복되고 있다.",
    pangyo_article.published_at = date("2026-04-28"),
    pangyo_article.source = "sample",
    pangyo_article.url = "https://example.com/news/a006",
    pangyo_article.importance_score = 0.7;

MATCH (article:NewsArticle {article_id: "A001"}), (gpt:Technology {normalized_name: "gpt"})
MERGE (article)-[:MENTIONS_TECH]->(gpt);

MATCH (article:NewsArticle {article_id: "A001"}), (openai:Company {normalized_name: "openai"})
MERGE (article)-[:MENTIONS_COMPANY]->(openai);

MATCH (article:NewsArticle {article_id: "A001"}), (update_event:Event {normalized_name: "업데이트"})
MERGE (article)-[:DESCRIBES_EVENT]->(update_event);

MATCH (pangyo_article:NewsArticle {article_id: "A006"}), (cloud:Technology {normalized_name: "클라우드"})
MERGE (pangyo_article)-[:MENTIONS_TECH]->(cloud);

MATCH (pangyo_article:NewsArticle {article_id: "A006"}), (investment_event:Event {normalized_name: "투자회복"})
MERGE (pangyo_article)-[:DESCRIBES_EVENT]->(investment_event);
