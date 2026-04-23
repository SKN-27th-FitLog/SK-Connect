from typing import List, Dict, Any
from datetime import datetime
from src.core.registry import get_collector, get_parser, get_stage
import logging

logger = logging.getLogger(__name__)

class PipelineOrchestrator:
    """
    설계안 2, 11장 준수 - 파이프라인 통합 제어 클래스.
    Registry를 통해 모든 Stage와 플랫폼별 컴포넌트를 동적으로 로드.
    """
    def __init__(self, platform: str = "DiningCode"):
        # 1. 컴포넌트 초기화
        self.collector = get_collector(platform)
        self.parser = get_parser(platform)
        
        # 2. Stage 초기화 (Registry 활용)
        self.stage0 = get_stage("target_selection")
        self.stage1 = get_stage("raw_collection", collector=self.collector)
        self.stage2 = get_stage("candidate_parsing", parser=self.parser)
        self.stage3 = get_stage("validation_normalization")
        self.stage4 = get_stage("load")
        self.stage5 = get_stage("fail_classification")

    def _generate_batch_id(self, category_cd: str) -> str:
        """batch_id 생성 규칙"""
        now = datetime.now()
        return f"{now.strftime('%Y%m%d')}_{category_cd}_{now.strftime('%H%M%S')}"

    async def run(self, category_cd: str):
        """파이프라인 전체 실행 흐름"""
        batch_id = self._generate_batch_id(category_cd)
        logger.info(f"--- Pipeline Started ({batch_id}) ---")
        
        all_failures = []
        try:
            # S0: 대상 선정
            targets = self.stage0.execute(category_cd)
            if not targets: return

            # S1: 수집
            raw_results = await self.stage1.execute(targets, batch_id, category_cd)
            all_failures.extend([r for r in raw_results if r["status"] == "fail"])
            success_raws = [r for r in raw_results if r["status"] == "success"]

            # S2: 파싱
            candidates = self.stage2.execute(success_raws, batch_id, category_cd)

            # S3: 정규화
            normalized = self.stage3.execute(candidates, batch_id, category_cd)

            # S4: 적재
            load_results = self.stage4.execute(normalized, batch_id, category_cd)
            all_failures.extend([r for r in load_results if r["status"] == "fail"])

            # S5: 실패 처리
            if all_failures:
                self.stage5.execute(all_failures, batch_id, category_cd)

            logger.info(f"--- Pipeline Finished ({batch_id}) ---")
        except Exception as e:
            logger.critical(f"Pipeline Crash: {str(e)}", exc_info=True)
            raise
