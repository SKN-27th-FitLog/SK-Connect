CREATE CONSTRAINT restaurant_id IF NOT EXISTS
FOR (n:Restaurant) REQUIRE n.restaurant_id IS UNIQUE;

CREATE CONSTRAINT area_normalized_name IF NOT EXISTS
FOR (n:Area) REQUIRE n.normalized_name IS UNIQUE;

CREATE CONSTRAINT menu_normalized_name IF NOT EXISTS
FOR (n:Menu) REQUIRE n.normalized_name IS UNIQUE;

CREATE CONSTRAINT ingredient_normalized_name IF NOT EXISTS
FOR (n:Ingredient) REQUIRE n.normalized_name IS UNIQUE;

CREATE CONSTRAINT tag_normalized_name IF NOT EXISTS
FOR (n:Tag) REQUIRE n.normalized_name IS UNIQUE;

CREATE CONSTRAINT news_article_id IF NOT EXISTS
FOR (n:NewsArticle) REQUIRE n.article_id IS UNIQUE;

CREATE CONSTRAINT topic_normalized_name IF NOT EXISTS
FOR (n:Topic) REQUIRE n.normalized_name IS UNIQUE;

CREATE CONSTRAINT technology_normalized_name IF NOT EXISTS
FOR (n:Technology) REQUIRE n.normalized_name IS UNIQUE;

CREATE CONSTRAINT company_normalized_name IF NOT EXISTS
FOR (n:Company) REQUIRE n.normalized_name IS UNIQUE;

CREATE CONSTRAINT event_normalized_name IF NOT EXISTS
FOR (n:Event) REQUIRE n.normalized_name IS UNIQUE;

CREATE CONSTRAINT concept_normalized_name IF NOT EXISTS
FOR (n:Concept) REQUIRE n.normalized_name IS UNIQUE;

CREATE INDEX restaurant_rating IF NOT EXISTS
FOR (n:Restaurant) ON (n.rating);

CREATE INDEX restaurant_avg_price IF NOT EXISTS
FOR (n:Restaurant) ON (n.avg_price);

CREATE INDEX news_published_at IF NOT EXISTS
FOR (n:NewsArticle) ON (n.published_at);
