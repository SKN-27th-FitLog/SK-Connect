MERGE (pangyo:Concept {normalized_name: "판교"})
SET pangyo.concept_id = "CONCEPT001", pangyo.name = "판교", pangyo.concept_type = "location";

MERGE (ai:Concept {normalized_name: "ai"})
SET ai.concept_id = "CONCEPT002", ai.name = "AI", ai.concept_type = "technology_area";

MATCH (plain_meat:Restaurant {restaurant_id: "R006"}), (pangyo:Concept {normalized_name: "판교"})
MERGE (plain_meat)-[:RELATED_TO]->(pangyo);

MATCH (pangyo_article:NewsArticle {article_id: "A006"}), (pangyo:Concept {normalized_name: "판교"})
MERGE (pangyo_article)-[:RELATED_TO]->(pangyo);

MATCH (article:NewsArticle {article_id: "A001"}), (ai:Concept {normalized_name: "ai"})
MERGE (article)-[:RELATED_TO]->(ai);
