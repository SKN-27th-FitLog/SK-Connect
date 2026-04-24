
from django.db import connection
import time

from logging_config import set_logging
logger = set_logging()

class get_crawling_data():
    def __init__(self):
        self.BATCH_SIZE = 100

    def merge_data(self, data:list[dict]) -> list[dict]:
        """각 4개의 테이블에서 가져온 데이터들을 crawling_id를 기준으로 하나의 데이터로 합친다"""
        try:
            result:dict = {}

            # data를 crawling_id 기준으로 병합 (중복 id는 빈 값만 보강)
            for row in data:
                crawling_id = row.get('crawling_id')
                if crawling_id is None:
                    logger.warning("skip row without crawling_id", extra={"row": row})
                    continue

                if crawling_id not in result:
                    result[crawling_id] = dict(row)
                else:
                    merged = result[crawling_id]
                    for key, value in row.items():
                        # 기존 값이 비어 있을 때만 새 값으로 채운다.
                        if merged.get(key) in (None, "") and value not in (None, ""):
                            merged[key] = value

                logger.debug(f"crawling_id={crawling_id} merged")
                

        #예외 발생시 크롤링 id 로그 기록
        except Exception as e:
            print(f"Error: {e}")
            logger.error(f"Error={e} | crawling_id={row['crawling_id']}")
            return None
        
        #합친 데이터를 리스트로 반환
        return list(result.values())

    def cursor_excute(self, query: str, params: list)->list[dict]:
        """쿼리 실행 후 결과를 딕셔너리 리스트로 반환"""
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]

    def route_crawling_data(self, row:list[dict]):
        """category_cd에 따라 분기하여 데이터를 반환"""
        batch_count = 0
        while True:
            try:
                if row['category_cd'] == 'IC02':
                    return row
                elif row['category_cd'] == 'IC01':
                    data = self.merge_data(self.get_shop_crawling_data())
                    return data
                elif row['category_cd'] != 'IC02' or row['category_cd'] != 'IC01':
                    raise ValueError("Invalid category_cd")

            except Exception as e:
                print(f"Error: {e}")
                logger.error(f"Error={e} | crawling_id={row['crawling_id']}")
                continue
            
            print(f"Batch {batch_count} completed...")
            batch_count += 1
            time.sleep(1)

    def get_crawling_data(self):
        """crawling 테이블에서 category_cd가 'IC02'인 데이터를 조회
            posts 테이블에서 crawling_id가 없는 데이터를 조회"""
        query = """
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
        rows = self.cursor_excute(query, params = ['IC02', self.BATCH_SIZE])
        return rows


    def get_shop_crawling_data(self):
        #4개의 테이블에서 map_id를 기준으로 하나의 데이터로 합친다
        #각 maps, crawling, shop, menu 테이블에서 데이터를 가져온다
        query = """
        SELECT m.*, c.*, s.*, menu.*
        FROM maps m
        LEFT JOIN crawling c ON m.map_id = c.map_id
        LEFT JOIN shop s ON m.map_id = s.map_id
        LEFT JOIN menu ON s.shop_id = menu.shop_id
        WHERE m.category_cd = %s
        AND m.created_at >= (
            SELECT MAX(p.created_at)
            FROM posts p
        )
        """
        data = self.merge_data()

        self.rows = self.cursor_excute(query, params = ['shop', self.BATCH_SIZE])
        return self.rows


