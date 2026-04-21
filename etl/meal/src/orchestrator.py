import os
from typing import List, Dict, Optional, Any
import pandas as pd
from .core.file_manager import logger, file_manager
from .core.db_client import DBClient
from ..core.services.kakao_api import KakaoAPI
from .core.code_manager.loader import CSVCodeLoader
from .core.code_manager.resolver import CodeResolver
from .core.db.sync_service import DBSyncService
from .core.constants.pipeline_constants import PipelineQuota, CrawlerThread, LoadStatus, ProcessType

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
    고도화된 ETL 파이프라인 조율 및 운영 정책(Quota, Recovery, Deduplication)을 강제합니다.
    (v4.0 Enterprise Architecture)
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.db = DBClient(config["db_params"])
        self.kakao = KakaoAPI(config["kakao_api_key"])
        
        # 1. 인프라 초기화
        code_loader = CSVCodeLoader(config["code_table_path"])
        self.resolver = CodeResolver(code_loader)
        self.sync_service = DBSyncService(self.db)
        
        # 2. 파이프라인 컴포넌트 초기화
        self.link_extractor = LinkExtractor(headless=config.get("headless", True))
        self.shop_extractor = DiningCodeExtractor(headless=config.get("headless", True))
        self.review_extractor = ReviewExtractor(headless=config.get("headless", True))
        
        self.shop_processor = ShopProcessor(self.resolver)
        self.review_processor = ReviewProcessor()
        
        self.shop_loader = ShopLoader(self.db, self.kakao, self.shop_processor)
        self.post_loader = PostLoader(self.db)
        self.review_loader = ReviewLoader(self.db)

        # 3. Quota 및 상태 관리
        self.new_shop_count = 0
        self.shop_limit = config.get("daily_limit", PipelineQuota.DAILY_NEW_SHOP_LIMIT)

    def run_full_pipeline(self, target_csv: str):
        logger.info("=" * 60)
        logger.info(f"--- [Orchestrator] v4.0 가동 (Quota: {self.shop_limit})")
        logger.info("=" * 60)
        
        try:
            # [Step 1] 링크 수집
            df_links = self._step_extract_links(target_csv)
            if df_links.empty: return

            # [Step 2] 매장 상세 정보 수집 (Quota 체크 및 사전 중복 체크 포함)
            df_shops_raw = self._step_extract_shop_details(df_links)
            
            if not df_shops_raw.empty:
                # [Step 3] Shop Loader 실행
                shop_stats = self.shop_loader.load_all(df_shops_raw)
                self.new_shop_count = shop_stats["success"]
                logger.info(f"--- [Quota Progress] {self.new_shop_count} / {self.shop_limit} Shops Loaded")

                # [Step 4] 리뷰 및 포스트 처리 (Quota 내에서 수집된 매장 대상)
                self._step_handle_reviews(df_links.head(len(df_shops_raw)))
                self.post_loader.load_all(df_shops_raw)

            logger.info("*" * 60)
            logger.info(f" [+] 파이프라인 종료 (최종 신규 적재: {self.new_shop_count}건)")
            logger.info("*" * 60)

        except Exception as e:
            logger.error(f"!!! ETL 중 치명적 오류 발생: {e}")
            raise

    def run_recovery_mode(self):
        """
        [Phase 1] status=fail 폴더 내의 CSV 파일들을 재처리합니다.
        성공 시 archive 경로로 이동합니다.
        """
        logger.info("--- [RECOVERY] 실패 데이터 재처리 모드 가동")
        fail_files = file_manager.list_hive_files(status=LoadStatus.FAIL.value)
        
        for file_path in fail_files:
            try:
                df_fail = pd.read_csv(file_path)
                logger.info(f"--- [RECOVERY] 파일 처리 중: {os.path.basename(file_path)}")
                
                # 재처리 로직 (단순 재적재 시도)
                # 서비스명에 따라 로더 분기
                if "shop" in file_path:
                    stats = self.shop_loader.load_all(df_fail)
                    if stats["success"] > 0:
                        # 성공 시 아카이브 이동
                        file_manager.move_to_archive(file_path)
                elif "review" in file_path:
                    self.review_loader.load_all(df_fail)
                    file_manager.move_to_archive(file_path)
                
            except Exception as e:
                logger.error(f"!!! Recovery 중 데이터 처리 실패 ({file_path}): {e}")

    def _step_extract_links(self, target_csv: str) -> pd.DataFrame:
        targets = self._read_targets(target_csv)
        all_links = []
        for t in targets:
            links = self.link_extractor.extract_links(t["region"], t["category"])
            # [Optimization] 수집 단계에서 이미 DB에 있는 URL은 필터링 가능
            filtered_links = [l for l in links if not self.sync_service.exists_in_db("maps", {"source_url": l["store_url"]})[0]]
            all_links.extend(filtered_links)
        
        return pd.DataFrame(all_links).drop_duplicates(subset=["store_url"])

    def _step_extract_shop_details(self, df_links: pd.DataFrame) -> pd.DataFrame:
        results = []
        for _, row in df_links.iterrows():
            # Quota 도달 시 중단
            if self.new_shop_count >= self.shop_limit:
                logger.warning(f"--- [QUOTA] 일일 수집 한도({self.shop_limit})에 도달하였습니다.")
                break

            details = self.shop_extractor.extract_details(row["store_url"], row["store_name"])
            details["source_category"] = row.get("source_category", "")
            results.append(details)
            
        return pd.DataFrame(results)

    def _step_handle_reviews(self, df_links: pd.DataFrame):
        all_reviews_raw = []
        for _, row in df_links.iterrows():
            rv_list = self.review_extractor.extract_reviews(row["store_url"], row["store_name"])
            all_reviews_raw.extend(rv_list)
        
        if all_reviews_raw:
            df_raw = pd.DataFrame(all_reviews_raw)
            self.review_loader.load_all(df_raw)

    def _read_targets(self, path: str) -> List[Dict[str, str]]:
        import csv
        targets = []
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("region") and row.get("category"):
                        targets.append(row)
        except Exception as e:
            logger.error(f"!!! 타겟 파일 로드 실패: {e}")
        return targets
