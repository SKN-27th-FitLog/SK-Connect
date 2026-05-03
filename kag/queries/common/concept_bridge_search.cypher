MATCH (concept:Concept {normalized_name: $concept_name})
CALL {
  WITH concept
  MATCH restaurant_path = (restaurant:Restaurant)-[:RELATED_TO]->(concept)
  RETURN restaurant AS result_node,
         collect(restaurant_path) AS evidence_paths,
         0.8 AS score
  UNION
  WITH concept
  MATCH article_path = (article:NewsArticle)-[:RELATED_TO]->(concept)
  RETURN article AS result_node,
         collect(article_path) AS evidence_paths,
         0.8 AS score
}
RETURN result_node,
       evidence_paths,
       {
         concept: concept.normalized_name,
         result_type: labels(result_node)[0]
       } AS applied_conditions,
       score;
