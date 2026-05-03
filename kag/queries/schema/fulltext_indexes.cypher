CREATE FULLTEXT INDEX restaurant_text_index IF NOT EXISTS
FOR (n:Restaurant) ON EACH [n.name, n.description, n.address];

CREATE FULLTEXT INDEX food_condition_text_index IF NOT EXISTS
FOR (n:Menu|Ingredient|Tag) ON EACH [n.name, n.normalized_name];

CREATE FULLTEXT INDEX news_text_index IF NOT EXISTS
FOR (n:NewsArticle) ON EACH [n.title, n.summary, n.content];

CREATE FULLTEXT INDEX news_condition_text_index IF NOT EXISTS
FOR (n:Topic|Technology|Company|Event) ON EACH [n.name, n.normalized_name];
