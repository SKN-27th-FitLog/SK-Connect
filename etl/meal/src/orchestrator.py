import os
from typing import List, Dict, Optional, Any
import pandas as pd
from .core.file_manager import logger, file_manager
from .core.db_client import DBClient
from .core.services.kakao_api import KakaoAPI

# Extractors
from .extractors.link_extractor import LinkExtractor
from .extractors.diningcode_extractor import DiningCodeExtractor
from .extractors.review_extractor import ReviewExtractor

# Processors (Transformers)
from .transformers.shop_processor import ShopProcessor
from .transformers.review_processor import ReviewProcessor

# Loaders
from .loaders.shop_loader import ShopLoader
from .loaders.post_loader import PostLoader
from .loaders.review_loader import ReviewLoader

class ETLOrchestrator:
    """
    단계별 적재 규약을 준수하며 전체 ETL을 조율합니다.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        self.db = DBClient(config["db_params"])
        self.kakao = KakaoAPI(config["kakao_api_key"])
        
        self.link_extractor = LinkExtractor(headless=config.get("headless", True))
        self.shop_extractor = DiningCodeExtractor(headless=config.get("headless", True))
        self.review_extractor = ReviewExtractor(headless=config.get("headless", True))
        
        self.shop_processor = ShopProcessor(config["code_table_path"])
        self.review_processor = ReviewProcessor()
        
        self.shop_loader = ShopLoader(self.db, self.kakao, self.shop_processor)
        self.post_loader = PostLoader(self.db)
        self.review_loader = ReviewLoader(self.db)

    def run_full_pipeline(self, target_csv: str, limit: Optional[int] = None):
        logger.info("=" * 60)
        logger.info("--- [Orchestrator] ETL 파이프라인 가동 시작")
        logger.info("=" * 60)
        
        try:
            # [Step 1] 링크 수집
            df_links = self._step_extract_links(target_csv, limit)
            if df_links.empty: return

            # [Step 2] 매장 상세 정보 (Shop Master & Post)
            df_shops_raw = self._step_extract_shop_details(df_links)
            
            # Shop Master 적재 (maps, shop, menu 등 내부 Hive 저장 포함)
            self.shop_loader.load_all(df_shops_raw)
            
            # Shop Post 적재 (crawling thread='shop')
            df_shops_cleansed_post = self.shop_processor.process_batch_crawling(df_shops_raw)
            self.post_loader.load_all(df_shops_raw, df_shops_cleansed_post)

            # [Step 3] 리뷰 정보
            self._step_handle_reviews(df_links)

            logger.info("*" * 60)
            logger.info(" [+] 모든 ETL 프로세스가 성공적으로 완료되었습니다.")
            logger.info("*" * 60)

        except Exception as e:
            logger.error(f"!!! ETL 중 치명적 오류 발생: {e}")
            raise

    def _step_extract_links(self, target_csv: str, limit: int) -> pd.DataFrame:
        targets = self._read_targets(target_csv)
        all_links = []
        for t in targets:
            links = self.link_extractor.extract_links(t["region"], t["category"])
            all_links.extend(links)
        
        df = pd.DataFrame(all_links).drop_duplicates(subset=["store_url"])
        if limit and not df.empty:
            df = df.head(limit)
        return df

    def _step_extract_shop_details(self, df_links: pd.DataFrame) -> pd.DataFrame:
        results = []
        for _, row in df_links.iterrows():
            details = self.shop_extractor.extract_details(row["store_url"], row["store_name"])
            details["source_category"] = row["source_category"]
            results.append(details)
        return pd.DataFrame(results)

    def _step_handle_reviews(self, df_links: pd.DataFrame):
        all_reviews_raw = []
        for _, row in df_links.iterrows():
            rv_list = self.review_extractor.extract_reviews(row["store_url"], row["store_name"])
            all_reviews_raw.extend(rv_list)
        
        if all_reviews_raw:
            df_raw = pd.DataFrame(all_reviews_raw)
            df_cleansed = self.review_processor.process_batch(df_raw)
            self.review_loader.load_all(df_raw, df_cleansed)

    def _read_targets(self, path: str) -> List[Dict[str, str]]:
        import csv
        targets = []
        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                region = str(row.get("region", "")).strip()
                cat = str(row.get("category", "")).strip()
                if region and cat:
                    targets.append({"region": region, "category": cat})
        return targets
