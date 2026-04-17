import pandas as pd
from typing import Dict, Any, List
from ..core.db_client import DBClient
from ..core.file_manager import logger, file_manager
from ..core.constants import Category

class PostLoader:
    """
    매장 상세 포스팅 데이터의 [Raw -> Cleansing -> DB Load -> Save] 단계를 관리합니다.
    """
    
    def __init__(self, db_client: DBClient):
        self.db = db_client

    def load_all(self, df_raw: pd.DataFrame, df_cleansed: pd.DataFrame, truncate_shop_posts: bool = False):
        if df_raw.empty or df_cleansed.empty:
            logger.warning("--- [LOADER] 처리할 포스팅 데이터가 없습니다.")
            return 0

        # 1. RAW 저장 (원본 파일은 ShopLoader와 공유될 수 있지만 규약상 개별 서비스로 관리 가능)
        # 하지만 중복 저장을 피하려면 Orchestrator에서 조율하거나, 명시적으로 저장합니다.
        # 여기서는 규약 준수를 위해 'shop' 서비스의 raw로 저장합니다.
        file_manager.save_df(df_raw, "raw", "shop", "success")

        # 2. CLEANSING 저장
        file_manager.save_df(df_cleansed, "cleansing", "shop", "success")

        # 3. DB 적재 (crawling 테이블 thread='shop')
        success_count = self._load_to_db(df_cleansed, truncate_shop_posts)

        # 4. SAVE 저장
        if success_count > 0:
            file_manager.save_df(df_cleansed, "save", "shop", "success")
            
        return success_count

    def _load_to_db(self, df: pd.DataFrame, truncate_shop_posts: bool):
        def task(conn, cur):
            if truncate_shop_posts:
                logger.info("--- crawling 테이블 내 기존 매장 데이터 초기화 중...")
                cur.execute("DELETE FROM crawling WHERE thread = 'shop'")
            
            success = 0
            for _, r in df.iterrows():
                try:
                    # map_id 조회
                    store_name = str(r.get("title", ""))
                    content_str = str(r.get("content", ""))
                    store_address = ""
                    if "주소: " in content_str:
                        store_address = content_str.split("\n")[0].replace("주소: ", "").strip()

                    cur.execute(
                        "SELECT map_id FROM maps WHERE name = %s AND address_detail = %s",
                        (store_name, store_address)
                    )
                    row = cur.fetchone()
                    map_id = row[0] if row else None

                    # crawling INSERT
                    columns = ["title", "content", "thread", "article_url", "created_at",
                               "view_count", "comment_count", "point", "author", "map_id", "category_cd"]
                    query = f"INSERT INTO crawling ({', '.join(columns)}) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                    val = (
                        store_name, content_str, "shop", str(r.get("article_url")),
                        r.get("created_at"), int(r.get("view_count", 0)), int(r.get("comment_count", 0)),
                        float(r.get("point", 0.0)), str(r.get("author", "crawler_bot")),
                        map_id, str(r.get("category_cd", Category.RESTAURANT.value))
                    )
                    cur.execute(query, val)
                    success += 1
                except Exception as e:
                    logger.error(f"!!! 포스팅 개별 적재 실패: {e}")
            return success

        return self.db.execute_transaction(task)
