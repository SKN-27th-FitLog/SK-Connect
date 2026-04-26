from dotenv import load_dotenv
from pathlib import Path
from psycopg2 import connect
import os

from src.logging_config import set_logging
from src.merge_utils import apply_merge_rules

logger = set_logging()
env_path = Path(__file__).resolve().parents[3] / "database" / ".env"
load_dotenv(env_path, override=True)


class _Connection:
    _instance = None

    @classmethod
    def get_connection(cls):
        if cls._instance is None:
            cls._instance = connect(
                host=os.getenv("DB_HOST"),
                port=os.getenv("DB_PORT"),
                database=os.getenv("SERVICE_DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
            )
        return cls._instance


class GetCrawlingData():
    def __init__(self):
        self.BATCH_SIZE = 100
        self.CATEGORY_CD = {
            "IC01": "casual", #food
            "IC02": "formal", #IT
        }

    def merge_data(self, row:dict, another_data:list[dict]) -> list[dict]:
        """각 4개의 테이블에서 가져온 데이터들을 crawling_id를 기준으로 하나의 데이터로 합친다"""
        try:
            is_matched = False
            # crawling 본문(content)은 조인으로 중복되므로 concat에서 제외
            concat_keys = ['metadata', 'keywords', 'menu_name', 'menu_price']
            fill_if_none_keys = ['content', 'article_url', 'author', 'view_count', 'comment_count', 'category_cd', 'map_id', 'shop_name']

            for r in another_data:
                if r['crawling_id'] != row['crawling_id']:
                    continue

                is_matched = True
                apply_merge_rules(
                    target=row,
                    incoming=r,
                    concat_keys=concat_keys,
                    fill_if_none_keys=fill_if_none_keys
                )

            if is_matched:
                if row.get("map_id") is None:
                    row["map_id"] = row.get("crawling_map_id")
                return row

            # 조인 데이터가 없어도 crawling 원본은 처리 대상이므로 그대로 반환
            return row
        #예외 발생시 크롤링 id 로그 기록
        except Exception as e:
            logger.error(f"Error={e} | crawling_id={row['crawling_id']}")
            return None


    def cursor_excute(self, query: str, params: list)->list[dict]:
        """쿼리 실행 후 결과를 딕셔너리 리스트로 반환"""
        try:
            with _Connection.get_connection().cursor() as cursor: #cursor 연결
                cursor.execute(query, params)
                columns = [col[0] for col in cursor.description] #컬럼 이름 가져오기
                rows = cursor.fetchall() #데이터 가져오기
            return [dict(zip(columns,row)) for row in rows] #데이터를 딕셔너리 리스트로 반환
            
        except Exception as e:
            print(f"Error: {e}")
            logger.error(f"Error={e}") #crawling_id를 함께 로깅
            _Connection.get_connection().rollback()
            return None

    def route_crawling_data(self):
        """category_cd에 따라 분기, 데이터를 반환"""
        try:
            #crawling테이블에서 데이터를 가져옴 + 해당 데이터의 type을 확인
            data:list[dict] = self.get_crawling_data()
            if not data:
                return []
            type = data[0]['category_cd']

            if type not in self.CATEGORY_CD:
                logger.error(f"Error=Invalid category_cd({type})")
                return []

            if type == 'IC02': #crawling테이블에서만 데이터를 가져오는 경우
                return data

            # IC01: 식당성 데이터는 map/shop/menu 조인 후 merge
            result:list[dict] = []
            another_data = self.get_shop_crawling_data(type)

            #another_data가 없는 경우
            if another_data is None:
                raise ValueError("another_data is None")

            #data를 하나씩 가져오면서 another_data와 합침
            for row in data:
                merged_data = self.merge_data(row, another_data)

                if merged_data is not None:
                    result.append(merged_data)
                elif merged_data is None:
                    continue
            return result

        except Exception as e:
            print(f"Error: {e}")
            if 'data' in locals() and data:
                logger.error(f"Error={e} | crawling_id={data[0]['crawling_id']} ~ {data[-1]['crawling_id']}")
            else:
                logger.error(f"Error={e}")
            return []

    def get_crawling_data(self):
        """crawling 테이블에서 데이터를 조회
            posts 테이블에 동일 title+map_id가 없는 데이터를 조회"""
        query = """
            SELECT c.*
            FROM crawling c
            WHERE c.crawling_id IS NOT NULL
            AND c.content IS NOT NULL
            AND NULLIF(TRIM(c.content), '') IS NOT NULL
            AND (c.title IS NULL OR c.title NOT ILIKE 'crawl%%')
            AND NOT EXISTS (
                SELECT 1
                FROM posts p
                WHERE p.title = c.title
                AND (
                    p.map_id = c.map_id
                    OR (p.map_id IS NULL AND c.map_id IS NULL)
                )
            )
            ORDER BY c.crawling_id ASC
            LIMIT %s;
            """
        rows = self.cursor_excute(query, params = [self.BATCH_SIZE])
        return rows


    def get_shop_crawling_data(self, category_cd: str):
        """4개의 테이블에서 crawling_id를 기준으로 하나의 데이터로 합친다."""
        query = """
        SELECT
            c.*,
            c.map_id as crawling_map_id,
            m.map_id as maps_map_id,
            m.name as shop_name,
            menu.name as menu_name,
            menu.price as menu_price
        FROM crawling c
        LEFT JOIN maps m ON c.map_id = m.map_id
        LEFT JOIN shop s ON m.map_id = s.map_id
        LEFT JOIN menu ON s.shop_id = menu.shop_id
        WHERE c.crawling_id IS NOT NULL
        AND c.category_cd = %s
        ORDER BY c.crawling_id ASC
        LIMIT %s
        """
        try:
            another_data = self.cursor_excute(query, params = [category_cd, self.BATCH_SIZE])
            return another_data

        except Exception as e:
            logger.error(f"Error={e}")
            return None

