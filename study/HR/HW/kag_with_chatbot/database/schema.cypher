// Constraints
CREATE CONSTRAINT restaurant_id_unique IF NOT EXISTS FOR (r:Restaurant) REQUIRE r.id IS UNIQUE;
CREATE CONSTRAINT user_session_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.session_id IS UNIQUE;
CREATE CONSTRAINT tag_name_unique IF NOT EXISTS FOR (t:Tag) REQUIRE t.name IS UNIQUE;
CREATE CONSTRAINT area_name_unique IF NOT EXISTS FOR (a:Area) REQUIRE a.name IS UNIQUE;

// Indexes
CREATE INDEX restaurant_name_index IF NOT EXISTS FOR (r:Restaurant) ON (r.name);
CREATE INDEX tag_name_index IF NOT EXISTS FOR (t:Tag) ON (t.name);
CREATE INDEX area_name_index IF NOT EXISTS FOR (a:Area) ON (a.name);
