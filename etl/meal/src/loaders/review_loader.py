import json
import pandas as pd
from typing import Dict, List, Any
from ..core.db_client import DBClient
from ..core.file_manager import logger
from .base_loader import BaseLoader
from ..core.constants.schema_constants import CrawlingColumns
from ..core.constants.pipeline_constants import LoadStatus, ProcessType, CrawlerThread

class ReviewLoader(BaseLoader):
    """
    리뷰 데이터를 crawling 테이블에 적재하며, 중복 체크와 스키마 검증을 수행합니다.
    (v4.0: BaseLoader 상속 및 Schema Contract 적용)
    """
    
    def __init__(self, db_client: DBClient):
        super().__init__(db_client)
        self.thread = CrawlerThread.REVIEW.value

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
                logger.info(f"--- [SKIP] 이미 존재하는 리뷰: {item[CrawlingColumns.ARTICLE_URL.value]}")
                continue
                
            if self._load_single_item(item):
                success_items.append(item)

        # 5. [SAVE] 단계 저장
        if success_items:
            self.save_with_status(pd.DataFrame(success_items), ProcessType.SAVE, self.thread, LoadStatus.SUCCESS)

        return {"success": len(success_items), "fail": len(fail_items)}

    def _preprocess(self, row: pd.Series) -> Dict[str, Any]:
        return {
            CrawlingColumns.TITLE.value: str(row.get("store_name", "Unknown Review")),
            CrawlingColumns.CONTENT.value: str(row.get("content", "")),
            CrawlingColumns.THREAD.value: self.thread,
            CrawlingColumns.ARTICLE_URL.value: str(row.get("review_id", "")), # 식별자로 사용
            CrawlingColumns.POINT.value: float(row.get("rating", 0.0)),
            "keywords": row.get("keywords", "[]") # keywords는 검증 대상에서 제외하거나 별도 처리
        }

    def _load_single_item(self, item: Dict[str, Any]) -> bool:
        def task(conn, cur):
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
