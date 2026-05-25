MATCH (tech:Technology {normalized_name: $technology_name})
MATCH (event:Event {normalized_name: $event_name})
MATCH tech_path = (article:NewsArticle)-[:MENTIONS_TECH]->(tech)
MATCH event_path = (article)-[:DESCRIBES_EVENT]->(event)
RETURN article AS result_node,
       collect(tech_path) + collect(event_path) AS evidence_paths,
       {
         interested_in: tech.normalized_name,
         requests: event.normalized_name
       } AS applied_conditions,
       coalesce(article.importance_score, 0.0) AS score
ORDER BY article.published_at DESC
LIMIT $limit;
