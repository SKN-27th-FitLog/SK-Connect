from typing import Dict, Any, List
from ..core.db_client import DBClient
from ..db.repositories.store_repository import StoreRepository
from .target_selection import TargetSelection
from .load_pipeline import LoadPipeline
from ..services.collectors.http_collector import HttpCollector
from ..services.parsers.store_parser import StoreParser
from ..core.constants.pipeline_constants import LoadStatus
from .dedup_service import DedupService
from .fail_classification import FailClassification
from ..core.file_manager import logger

class OrchestratorV4:
    """
    v4 설계 명세서를 따르는 통합 오케스트레이터입니다.
    Stage 0 ~ 5를 조율하며 일일 성공 목표를 달성합니다.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.db = DBClient(config["db_params"])
        self.store_repo = StoreRepository(self.db)
        
        # 파이프라인 스테이지 초기화
        self.target_selector = TargetSelection(self.db, None) 
        self.collector = HttpCollector(config.get("collector_config"))
        self.parser = StoreParser()
        self.dedup_service = DedupService(self.store_repo)
        self.loader = LoadPipeline(self.db, self.store_repo)
        self.fail_classifier = FailClassification(self.db)

    def run_daily_batch(self, category_cd: str, goal_count: int = 100):
        """
        특정 카테고리에 대한 일일 배치 수집을 실행합니다.
        """
        logger.info(f"========== [Orchestrator V4] Starting Batch for {category_cd} (Goal: {goal_count}) ==========")
        
        total_success = 0
        batch_id = None
        
        while total_success < goal_count:
            # Stage 0: 수집 대상 선정 (Search Mode)
            remaining = goal_count - total_success
            target_data = self.target_selector.run(category_cd, target_count=remaining)
            
            urls = target_data.get("candidate_store_ids", [])
            if not urls:
                logger.warning(f"--- [Orchestrator] No more targets available for {category_cd}")
                break
            
            batch_id = target_data["batch_id"]
            current_batch_results = []
            
            for url in urls:
                if total_success >= goal_count: break
                
                try:
                    # Stage 1: Raw 수집
                    raw = self.collector.collect(url)
                    if raw["status"] == LoadStatus.FAIL.value:
                        self.fail_classifier.classify_and_log(
                            stage="raw_collection",
                            reason_code=raw.get("reason_code", "NETWORK_ERROR"),
                            entity_id=url,
                            category_cd=category_cd,
                            batch_id=batch_id
                        )
                        continue
                    
                    # Stage 2: Parsing
                    candidate = self.parser.parse(raw["raw_content"])
                    if candidate.get("status") == "fail":
                        self.fail_classifier.classify_and_log(
                            stage="candidate_parsing",
                            reason_code="SELECTOR_MISMATCH",
                            entity_id=url,
                            category_cd=category_cd,
                            batch_id=batch_id
                        )
                        continue
                    
                    # URL 정보 추가 (Deduplication 및 Load 시 필요)
                    candidate["source_url"] = url
                    candidate["category_cd"] = category_cd
                    
                    # Stage 3: Dedup
                    dedup_info = self.dedup_service.get_dedup_info(candidate)
                    if dedup_info["is_duplicate"]:
                        logger.info(f"--- [SKIP] Duplicate found for {candidate.get('name')} ({url})")
                        continue
                        
                    current_batch_results.append(candidate)
                    
                except Exception as e:
                    logger.error(f"!!! [Orchestrator] Unexpected error for URL {url}: {e}")
            
            # Stage 4: Load
            if current_batch_results:
                load_res = self.loader.run(batch_id, current_batch_results)
                # LoadPipeline이 반환하는 요약 정보에서 성공 건수 추출
                success_count = load_res.get("summary", {}).get("success_count", 0)
                total_success += success_count
                logger.info(f"--- [Orchestrator] Batch Progress: {total_success}/{goal_count}")
                
            if not current_batch_results:
                break # 더 이상 진행할 후보가 없음

        logger.info(f"========== [Orchestrator V4] Finished. Total Success: {total_success} ==========")
