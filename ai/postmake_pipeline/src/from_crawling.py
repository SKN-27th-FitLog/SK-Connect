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
            # from_crawling 경로는 조회 전용이므로 autocommit으로 열린 트랜잭션 누수 방지
            cls._instance.autocommit = True
        return cls._instance


class GetCrawlingData():
    def __init__(self):
        self.BATCH_SIZE = 100
        self.CATEGORY_CD = {
            "IC01": "casual", #food
            "IC02": "formal", #IT
        }

    def merge_data(self, row: dict, another_data: list[dict]) -> list[dict]:
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


    def execute_query(self, query: str, params: list) -> list[dict]:
        """쿼리 실행 후 결과를 딕셔너리 리스트로 반환"""
        try:
            with _Connection.get_connection().cursor() as cursor:
                cursor.execute(query, params)
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]
            
        except Exception as e:
            logger.error(f"Error={e}") #crawling_id를 함께 로깅
            _Connection.get_connection().rollback()
            return None

    def route_crawling_data(self):
        """row별 category_cd에 따라 분기해 데이터를 반환"""
        try:
            # crawling 테이블에서 데이터를 가져옴
            data: list[dict] = self.get_crawling_data()
            if not data:
                return []

            result: list[dict] = []

            # IC01만 별도 조인 데이터를 미리 조회 (row별 분기에서 재사용)
            another_data_ic01 = self.get_shop_crawling_data("IC01")
            if another_data_ic01 is None:
                raise ValueError("another_data_ic01 is None")

            # row별 category_cd 기준 분기 처리
            for row in data:
                category_cd = row.get("category_cd")
                if category_cd not in self.CATEGORY_CD:
                    logger.error(f"Error=Invalid category_cd({category_cd})")
                    continue

                if category_cd == "IC02":
                    result.append(row)
                    continue

                # IC01: map/shop/menu 조인 후 merge
                merged_data = self.merge_data(row, another_data_ic01)
                if merged_data is not None:
                    result.append(merged_data)

            return result

        except Exception as e:
            if 'data' in locals() and data:
                logger.error(f"Error={e} | crawling_id={data[0]['crawling_id']} ~ {data[-1]['crawling_id']}")
            else:
                logger.error(f"Error={e}")
            return []

    def attach_existing_post_context(self, row: dict) -> dict:
        """동일 title+map_id 기존 post를 조회해 프롬프트 컨텍스트로 주입"""
        map_id = row.get("map_id")
        title = row.get("title")
        if map_id is None or not title:
            return row

        query = """
        SELECT post_id, title, content
        FROM posts
        WHERE LOWER(TRIM(title)) = LOWER(TRIM(%s))
            AND map_id = %s
            AND post_cd = %s
        ORDER BY modify_at DESC, post_id DESC
        LIMIT 3
        """
        existing_posts = self.execute_query(query, [title, map_id, "PT01"])
        if not existing_posts:
            return row

        row["existing_post_title"] = existing_posts[0].get("title")
        row["existing_post_count"] = len(existing_posts)
        row["existing_post_content"] = "\n\n".join(
            f"[기존글 {idx}] 제목: {post.get('title')}\n본문: {post.get('content')}"
            for idx, post in enumerate(existing_posts, start=1)
        )
        # LLM이 새 크롤링 본문과 기존 글 본문을 함께 재구성하도록 합성 컨텍스트를 제공
        current_content = str(row.get("content") or "").strip()
        row["generation_context_content"] = (
            f"[새 크롤링 본문]\n{current_content}\n\n"
            f"[기존 게시글 본문]\n{row['existing_post_content']}"
        )
        logger.info(
            "기존 게시글 컨텍스트 결합 완료 "
            f"(map_id={map_id}, title={title}, existing_count={len(existing_posts)})"
        )
        return row

    def get_crawling_data(self):
        """crawling 테이블에서 데이터를 조회
            동일 title+map_id 기준으로 이미 처리된 최신 crawling_id보다 큰 건만 조회"""
        query = """
            SELECT c.*
            FROM crawling c
            WHERE c.crawling_id IS NOT NULL
            AND c.content IS NOT NULL
            AND NULLIF(TRIM(c.content), '') IS NOT NULL
            AND (c.title IS NULL OR c.title NOT ILIKE 'crawl%%')
            AND (
                -- title/map 기준 매칭이 가능한 경우: 최신 처리 crawling_id보다 큰 데이터만 대상
                (
                    c.title IS NOT NULL
                    AND c.map_id IS NOT NULL
                    AND c.crawling_id > COALESCE((
                        SELECT MAX(p.crawling_id)
                        FROM posts p
                        WHERE p.post_cd = 'PT01'
                            AND p.crawling_id IS NOT NULL
                            AND LOWER(TRIM(p.title)) = LOWER(TRIM(c.title))
                            AND p.map_id = c.map_id
                    ), 0)
                )
                OR
                -- title/map 매칭이 불가능한 경우: crawling_id 기준 중복만 제거
                (
                    (c.title IS NULL OR c.map_id IS NULL)
                    AND NOT EXISTS (
                        SELECT 1
                        FROM posts p
                        WHERE p.crawling_id = c.crawling_id
                    )
                )
            )
            ORDER BY c.crawling_id ASC
            LIMIT %s;
            """
        rows = self.execute_query(query, params=[self.BATCH_SIZE])
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
            another_data = self.execute_query(query, params=[category_cd, self.BATCH_SIZE])
            return another_data

        except Exception as e:
            logger.error(f"Error={e}")
            return None

