
from django.db import connection


BATCH_SIZE = 100

def get_crawling_data(limit:int=BATCH_SIZE):
    get_query = """
SELECT c.*
FROM crawling c
WHERE c.category_cd = %s
AND c.created_at >= (
    SELECT MAX(p.created_at)
    FROM posts p
)
AND c.crawling_id IS NOT NULL
AND NOT EXISTS (
    SELECT 1
    FROM posts p
    WHERE p.crawling_id = c.crawling_id
)
ORDER BY c.crawling_id ASC
LIMIT %s;
"""
    with connection.cursor() as cursor:
        cursor.execute(get_query, ['it', limit])
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()

    return [dict(zip(columns, row)) for row in rows]

