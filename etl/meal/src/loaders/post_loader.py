import pandas as pd
from typing import Dict, List, Any
from ..core.db_client import DBClient
from ..core.file_manager import logger
from .base_loader import BaseLoader
from ..core.constants.schema_constants import CrawlingColumns
from ..core.constants.pipeline_constants import LoadStatus, ProcessType, CrawlerThread

class PostLoader(BaseLoader):
    """
    커뮤니티 포스트 데이터를 crawling 테이블에 적재하며, 중복 체크와 스키마 검증을 수행합니다.
    (v4.0: BaseLoader 상속 및 Schema Contract 적용)
    """
    
    def __init__(self, db_client: DBClient):
        super().__init__(db_client)
        self.thread = "post"

    def load_all(self, df_raw: pd.DataFrame) -> Dict[str, int]:
        if df_raw.empty:
            return {"success": 0, "fail": 0}

        # 1. CRAWLING(RAW) 저장
        self.save_with_status(df_raw, ProcessType.CRAWLING, self.thread, LoadStatus.SUCCESS)

        # 2. 전처리 및 검증
        valid_items = []
        fail_items = []
        
        for _, row in df_raw.iterrows():
            item = self._preprocess(row)
            
            # 스키마 검증
            is_valid, error = self.validator.validate("crawling", item)
            if not is_valid:
                item = self.record_failure(item, stage="validation", reason=error)
                fail_items.append(item)
                continue
            
            valid_items.append(item)

        # 3. [CLEANING] 단계 저장
        if valid_items:
            self.save_with_status(pd.DataFrame(valid_items), ProcessType.CLEANING, self.thread, LoadStatus.SUCCESS)
        if fail_items:
            self.save_with_status(pd.DataFrame(fail_items), ProcessType.CLEANING, self.thread, LoadStatus.FAIL)

        # 4. DB 적재 (중복 체크 포함)
        success_items = []
        for item in valid_items:
            # article_url 기준 중복 체크
            if self.sync_service.check_article_exists(self.thread, item[CrawlingColumns.ARTICLE_URL.value]):
                logger.info(f"--- [SKIP] 이미 존재하는 포스트: {item[CrawlingColumns.ARTICLE_URL.value]}")
                continue
                
            if self._load_single_item(item):
                success_items.append(item)

        # 5. [SAVE] 단계 저장
        if success_items:
            self.save_with_status(pd.DataFrame(success_items), ProcessType.SAVE, self.thread, LoadStatus.SUCCESS)

        return {"success": len(success_items), "fail": len(fail_items)}

    def _preprocess(self, row: pd.Series) -> Dict[str, Any]:
        return {
            CrawlingColumns.TITLE.value: str(row.get("title", "No Title")),
            CrawlingColumns.CONTENT.value: str(row.get("content", "")),
            CrawlingColumns.THREAD.value: self.thread,
            CrawlingColumns.ARTICLE_URL.value: str(row.get("article_url", "")),
            CrawlingColumns.CREATED_AT.value: str(row.get("created_at", "")),
            CrawlingColumns.VIEW_COUNT.value: self.safe_int(row.get("view_count")),
            CrawlingColumns.COMMENT_COUNT.value: self.safe_int(row.get("comment_count")),
            CrawlingColumns.POINT.value: float(row.get("point", 0.0)),
            CrawlingColumns.AUTHOR.value: str(row.get("author", "anonymous"))
        }

    def _load_single_item(self, item: Dict[str, Any]) -> bool:
        def task(conn, cur):
            try:
                # map_id 조회
                store_name = item[CrawlingColumns.TITLE.value]
                content_str = item[CrawlingColumns.CONTENT.value]
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
                columns = [CrawlingColumns.TITLE.value, CrawlingColumns.CONTENT.value, CrawlingColumns.THREAD.value,
                           CrawlingColumns.ARTICLE_URL.value, CrawlingColumns.CREATED_AT.value,
                           CrawlingColumns.VIEW_COUNT.value, CrawlingColumns.COMMENT_COUNT.value,
                           CrawlingColumns.POINT.value, CrawlingColumns.AUTHOR.value, "map_id", "category_cd"]
                query = f"INSERT INTO crawling ({', '.join(columns)}) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                val = (
                    store_name, content_str, item[CrawlingColumns.THREAD.value],
                    item[CrawlingColumns.ARTICLE_URL.value], item[CrawlingColumns.CREATED_AT.value],
                    item[CrawlingColumns.VIEW_COUNT.value], item[CrawlingColumns.COMMENT_COUNT.value],
                    item[CrawlingColumns.POINT.value], item[CrawlingColumns.AUTHOR.value],
                    map_id, item.get("category_cd", "restaurant")
                )
                cur.execute(query, val)
                return True
            except Exception as e:
                logger.error(f"!!! 포스팅 개별 적재 실패: {e}")
                return False

        return self.db.execute_transaction(task)
