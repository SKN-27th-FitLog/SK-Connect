MATCH (menu:Menu {normalized_name: $menu_name})
MATCH (required:Tag {normalized_name: $required_tag})
MATCH (excluded:Tag {normalized_name: $excluded_tag})
MATCH path = (restaurant:Restaurant)-[:SELLS]->(menu)
MATCH tag_path = (restaurant)-[:HAS_TAG]->(required)
WHERE restaurant.is_active = true
  AND NOT EXISTS {
    MATCH (restaurant)-[:HAS_TAG]->(excluded)
  }
RETURN restaurant AS result_node,
       collect(path) + collect(tag_path) AS evidence_paths,
       {
         prefers: menu.normalized_name,
         requires: required.normalized_name,
         excludes: excluded.normalized_name,
         exclude_type: "tag",
         exclude_strength: $exclude_strength
       } AS applied_conditions,
       coalesce(restaurant.rating, 0.0) AS score
ORDER BY restaurant.rating DESC
LIMIT $limit;
