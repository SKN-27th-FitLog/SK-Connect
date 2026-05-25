-- Backfill crawling rows that are referenced by analysis but missing in crawling.
-- Review the preview SELECTs first, then run the transaction as one unit.

BEGIN;

-- Preview: rows that will be inserted.
SELECT
    COUNT(*) AS missing_crawling_count
FROM analysis AS a
LEFT JOIN crawling AS c
    ON c.crawling_id = a.crawling_id
WHERE a.crawling_id IS NOT NULL
  AND c.crawling_id IS NULL;

-- Preview: map_id values that would violate crawling.map_id -> maps.map_id.
-- This should be 0 before insert. Invalid map_id values are inserted as NULL below.
SELECT
    COUNT(*) AS invalid_map_id_count
FROM analysis AS a
LEFT JOIN crawling AS c
    ON c.crawling_id = a.crawling_id
LEFT JOIN maps AS m
    ON m.map_id = a.map_id
WHERE a.crawling_id IS NOT NULL
  AND c.crawling_id IS NULL
  AND a.map_id IS NOT NULL
  AND m.map_id IS NULL;

WITH orphan_analysis AS (
    SELECT DISTINCT ON (a.crawling_id)
        a.crawling_id,
        a.title,
        a.content,
        a.article_url,
        a.created_dt,
        a.score,
        a.map_id,
        a.category_cd,
        a.information_cd,
        a.shop_cd,
        a.keywords,
        m.map_id AS valid_map_id
    FROM analysis AS a
    LEFT JOIN crawling AS c
        ON c.crawling_id = a.crawling_id
    LEFT JOIN maps AS m
        ON m.map_id = a.map_id
    WHERE a.crawling_id IS NOT NULL
      AND c.crawling_id IS NULL
    ORDER BY a.crawling_id, a.created_dt DESC NULLS LAST
)
INSERT INTO crawling (
    crawling_id,
    title,
    content,
    thread,
    article_url,
    created_at,
    view_count,
    comment_count,
    point,
    author,
    map_id,
    category_cd,
    information_cd,
    shop_cd,
    keywords
)
SELECT
    crawling_id,
    title,
    content,
    'analysis_backfill',
    article_url,
    COALESCE(created_dt, NOW()),
    NULL,
    NULL,
    score,
    'analysis_backfill',
    valid_map_id,
    category_cd,
    information_cd,
    shop_cd,
    LEFT(COALESCE(keywords, ''), 100)
FROM orphan_analysis
ON CONFLICT (crawling_id) DO NOTHING;

-- Keep the sequence ahead of explicitly inserted crawling_id values.
SELECT setval(
    'crawling_crawling_id_seq',
    GREATEST(COALESCE((SELECT MAX(crawling_id) FROM crawling), 1), 1),
    true
);

-- Verification: should be 0 after the insert.
SELECT
    COUNT(*) AS remaining_missing_crawling_count
FROM analysis AS a
LEFT JOIN crawling AS c
    ON c.crawling_id = a.crawling_id
WHERE a.crawling_id IS NOT NULL
  AND c.crawling_id IS NULL;

COMMIT;
