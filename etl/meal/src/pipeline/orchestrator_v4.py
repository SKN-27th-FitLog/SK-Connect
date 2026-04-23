from typing import Dict, Any, List
from ..core.db_client import DBClient
# from ..core.code_manager.loader import DBCodeLoader
# from ..core.code_manager.resolver import CodeResolver
from ..repositories.store_repository import StoreRepository
from .target_selection import TargetSelection
from .load_pipeline import LoadPipeline
from ..collectors.http_collector import HttpCollector
from ..parsers.store_parser import StoreParser
from .dedup_service import DedupService
from .fail_classification import FailClassification
from ..core.file_manager import logger

class OrchestratorV4:
    """
    v4 설계 명세서를 따르는 통합 오케스트레이터입니다.
    Stage 0 ~ 5를 조율하며 일일 100건 성공 목표를 달성합니다.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.db = DBClient(config["db_params"])
        self.store_repo = StoreRepository(self.db)
        
        # 파이프라인 스테이지 초기화
        # resolver는 현재 skeleton 상태이므로 None 처리하거나 기본값 사용
        self.target_selector = TargetSelection(self.db, None) 
        self.collector = HttpCollector(config.get("collector_config"))
        self.parser = StoreParser()
        self.dedup_service = DedupService(self.store_repo)
        self.loader = LoadPipeline(self.db, self.store_repo)
        self.fail_classifier = FailClassification(self.db)

    def run_daily_batch(self, category_cd: str, goal_count: int = 100):
        """
        특정 카테고리에 대한 일일 배치 수집을 실행합니다.
        성공 건수가 goal_count에 도달할 때까지 보충 수집을 시도합니다.
        """
        logger.info(f"========== [Orchestrator V4] Starting Batch for {category_cd} (Goal: {goal_count}) ==========")
        
        total_success = 0
        batch_id = None
        
        while total_success < goal_count:
            # Stage 0: 수집 대상 선정 (부족분만큼 요청)
            remaining = goal_count - total_success
            targets = self.target_selector.run(category_cd) # TODO: limit 파라미터 연동
            
            if not targets.get("selected_targets"):
                logger.warning(f"--- [Orchestrator] No more targets available for {category_cd}")
                break
            
            batch_id = targets["batch_id"]
            current_batch_results = []
            
            for target in targets["selected_targets"]:
                if total_success >= goal_count: break
                
                try:
                    # Stage 1: Raw 수집
                    raw = self.collector.collect(target["url"])
                    if raw["status"] == "fail":
                        self.fail_classifier.classify_and_log(
                            stage="raw_collection",
                            reason_code=raw.get("reason", "NETWORK_ERROR"),
                            entity_id=target.get("id", "unknown"),
                            category_cd=category_cd
                        )
                        continue
                    
                    # Stage 2: Parsing
                    candidate = self.parser.parse(raw["raw_content"])
                    if candidate["status"] == "fail":
                        self.fail_classifier.classify_and_log(
                            stage="candidate_parsing",
                            reason_code="SELECTOR_MISMATCH",
                            entity_id=target.get("id", "unknown"),
                            category_cd=category_cd,
                            raw_path=raw.get("path")
                        )
                        continue
                    
                    # Stage 3: Dedup
                    dedup_info = self.dedup_service.get_dedup_info(candidate)
                    if dedup_info["is_duplicate"]:
                        logger.info(f"--- [SKIP] Duplicate found for {candidate.get('name')}")
                        continue
                        
                    current_batch_results.append(candidate)
                    
                except Exception as e:
                    logger.error(f"!!! [Orchestrator] Unexpected error for target {target}: {e}")
            
            # Stage 4: Load
            if current_batch_results:
                load_result = self.loader.run(batch_id, current_batch_results)
                # 실제 성공 건수 업데이트 (Load 단계에서 반환받는다고 가정)
                success_in_this_step = len(current_batch_results) 
                total_success += success_in_this_step
                logger.info(f"--- [Orchestrator] Batch Progress: {total_success}/{goal_count}")

        logger.info(f"========== [Orchestrator V4] Finished. Total Success: {total_success} ==========")
