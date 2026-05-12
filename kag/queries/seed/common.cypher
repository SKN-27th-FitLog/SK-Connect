MERGE (c_pangyo:Concept {normalized_name: "판교"})
SET c_pangyo.concept_id = "CONCEPT001", c_pangyo.name = "판교", c_pangyo.concept_type = "location";

MERGE (c_ai:Concept {normalized_name: "ai"})
SET c_ai.concept_id = "CONCEPT002", c_ai.name = "AI", c_ai.concept_type = "technology_area";

MERGE (c_startup:Concept {normalized_name: "스타트업"})
SET c_startup.concept_id = "CONCEPT003", c_startup.name = "스타트업", c_startup.concept_type = "industry";

MERGE (c_dev:Concept {normalized_name: "개발자"})
SET c_dev.concept_id = "CONCEPT004", c_dev.name = "개발자", c_dev.concept_type = "audience";

MERGE (c_gangnam:Concept {normalized_name: "강남"})
SET c_gangnam.concept_id = "CONCEPT005", c_gangnam.name = "강남", c_gangnam.concept_type = "location";

MATCH (r:Restaurant)-[:LOCATED_IN]->(area:Area)
MATCH (c:Concept {normalized_name: area.normalized_name})
MERGE (r)-[:RELATED_TO]->(c);

MATCH (a:NewsArticle)-[:MENTIONS]->(t:Topic)
MATCH (c:Concept {normalized_name: t.normalized_name})
MERGE (a)-[:RELATED_TO]->(c);
