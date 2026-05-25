MATCH (preferred:Menu {normalized_name: $menu_name})
MATCH (excluded:Ingredient {normalized_name: $excluded_ingredient})
MATCH path = (restaurant:Restaurant)-[:SELLS]->(menu:Menu)
WHERE restaurant.is_active = true
  AND (
    menu.normalized_name = preferred.normalized_name
    OR EXISTS {
      MATCH (menu)-[:RELATED_TO]->(preferred)
    }
  )
  AND NOT EXISTS {
    MATCH (menu)-[:CONTAINS]->(excluded)
  }
RETURN restaurant AS result_node,
       collect(path) AS evidence_paths,
       {
         prefers: preferred.normalized_name,
         excludes: excluded.normalized_name,
         exclude_type: "ingredient",
         exclude_strength: $exclude_strength
       } AS applied_conditions,
       coalesce(restaurant.rating, 0.0) AS score
ORDER BY restaurant.rating DESC
LIMIT $limit;
