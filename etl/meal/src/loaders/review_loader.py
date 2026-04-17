import json
import pandas as pd
from typing import Dict, Any, List, Optional
from ..core.db_client import DBClient
from ..core.file_manager import logger, file_manager
from ..core.constants import Category, CrawlerThread

class ReviewLoader:
    """
    리뷰 데이터의 [Raw -> Cleansing -> DB Load -> Save] 단계별 저장을 관리합니다.
    """
    
    def __init__(self, db_client: DBClient):
        self.db = db_client

    def load_all(self, df_raw: pd.DataFrame, df_cleansed: pd.DataFrame, truncate_reviews: bool = False):
        """
        리뷰 데이터를 받아서 파일 저장 및 DB 적재를 수행합니다.
        """
        if df_raw.empty or df_cleansed.empty:
            logger.warning("--- [LOADER] 처리할 리뷰 데이터가 없습니다.")
            return 0

        # 1. RAW 저장
        file_manager.save_df(df_raw, "raw", CrawlerThread.REVIEW.value, "success")

        # 2. CLEANSING 저장
        file_manager.save_df(df_cleansed, "cleansing", CrawlerThread.REVIEW.value, "success")

        # 3. DB 적재 (crawling 테이블 및 images 테이블)
        success_count = self._load_to_db(df_cleansed, truncate_reviews)

        # 4. SAVE 저장
        if success_count > 0:
            file_manager.save_df(df_cleansed, "save", CrawlerThread.REVIEW.value, "success")
            
        return success_count

    def _load_to_db(self, df: pd.DataFrame, truncate_reviews: bool):
        def task(conn, cur):
            if truncate_reviews:
                logger.info("--- crawling 테이블 내 기존 리뷰 데이터 초기화 중...")
                cur.execute("DELETE FROM crawling WHERE thread = %s", (CrawlerThread.REVIEW.value,))
            
            success = 0
            for _, r in df.iterrows():
                try:
                    # map_id 조회
                    article_url = str(r.get("article_url", ""))
                    cur.execute("SELECT map_id FROM crawling WHERE thread = %s AND article_url = %s", 
                                (CrawlerThread.SHOP.value, article_url))
                    row = cur.fetchone()
                    map_id = row[0] if row else None
                    
                    # crawling INSERT
                    columns = ["title", "content", "thread", "article_url", "created_at",
                               "view_count", "comment_count", "point", "author", "map_id", "category_cd"]
                    query = f"INSERT INTO crawling ({', '.join(columns)}) VALUES %s RETURNING crawling_id"
                    val = (
                        str(r.get("title")), str(r.get("content")), CrawlerThread.REVIEW.value, article_url, r.get("created_at"),
                        int(r.get("view_count", 0)), int(r.get("comment_count", 0)), float(r.get("point", 0.0)),
                        str(r.get("author", "crawler_bot")), map_id, str(r.get("category_cd", Category.RESTAURANT.value))
                    )
                    cur.execute(query, [val])
                    crawling_id = cur.fetchone()[0]

                    # images INSERT
                    self._load_images(cur, crawling_id, r.get("local_image_paths", "[]"))
                    success += 1
                except Exception as e:
                    logger.error(f"!!! 리뷰 개별 적재 실패: {e}")
            return success

        return self.db.execute_transaction(task)

    def _load_images(self, cur, crawling_id: int, paths_json: str):
        try:
            paths = json.loads(str(paths_json))
            for p in paths:
                cur.execute(
                    "INSERT INTO images (image_url, table_name, table_id) VALUES (%s, %s, %s)",
                    (p, "crawling", crawling_id)
                )
        except: pass
