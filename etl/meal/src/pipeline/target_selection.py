import uuid
import json
from datetime import datetime, date
from typing import List, Dict, Any, Optional

from .base_stage import BaseStage
from ..core.file_manager import logger
from ..utils.decorators import trace_stage
from ..repositories.target_repository import TargetRepository
from ..models.target_models import DailyTarget, SelectionPolicy
from ..storage.hive_path_builder import HivePathBuilder

class TargetSelection(BaseStage):
    """
    Stage 0: Daily Target Selection
    설계서 v4 정책에 따라 일일 수집 목표(기본 100건)를 달성하기 위한 대상을 선정합니다.
    로직: 재시도 대상(Retry) 우선 확보 + 부족분 신규 후보(Source Pool) 보충
    """
    
    def __init__(self, db_client, resolver, path_builder: HivePathBuilder = None):
        super().__init__("Target Selection")
        self.db = db_client
        self.resolver = resolver
        self.target_repo = TargetRepository(db_client)
        self.path_builder = path_builder or HivePathBuilder()

    @trace_stage("Target Selection")
    def run(self, category_cd: str, target_count: int = 100) -> Dict[str, Any]:
        """
        수집 대상 선정의 진입점입니다.
        """
        # 1. 카테고리 유효성 확인 (Resolver가 있다면 활용)
        if self.resolver and hasattr(self.resolver, 'is_valid_category'):
            if not self.resolver.is_valid_category(category_cd):
                logger.error(f"!!! [Stage 0] Invalid category code: {category_cd}")
                return {"status": "fail", "reason": "INVALID_CATEGORY"}

        target_data = self._execute(category_cd, target_count)
        
        # 2. 결과 파일 저장 (Hive 경로 정책 적용)
        self._save_target_meta(target_data)
        
        return target_data.model_dump()

    def _execute(self, category_cd: str, target_count: int) -> DailyTarget:
        """
        DB 조회를 통해 실제 대상을 선정하는 핵심 로직입니다.
        """
        today = date.today()
        batch_id = self._generate_batch_id(category_cd, today.strftime("%Y-%m-%d"))
        
        logger.info(f"--- [Stage 0] Selecting targets for {category_cd} (Goal: {target_count})")
        
        # [Step 1] 재시도 대상 조회 (Fail Ledger에서 Retry Action인 건)
        retry_targets = self.target_repo.get_retry_targets(category_cd)
        retry_urls = [t['canonical_url'] for t in retry_targets]
        logger.info(f"--- [Stage 0] Found {len(retry_urls)} retry targets.")

        # [Step 2] 부족분만큼 신규 후보 추출 (Goal - Retry 건수)
        needed_count = max(0, target_count - len(retry_urls))
        new_candidates = []
        if needed_count > 0:
            candidates = self.target_repo.get_new_candidates(category_cd, limit=needed_count)
            new_candidates = [c['canonical_url'] for c in candidates]
            logger.info(f"--- [Stage 0] Supplemented {len(new_candidates)} new candidates.")

        # [Step 3] 최종 목록 병합
        final_target_urls = retry_urls + new_candidates
        
        # DailyTarget 모델 구성 (Pydantic 규약 준수)
        return DailyTarget(
            batch_id=batch_id,
            category_cd=category_cd,
            target_date=today,
            target_count=target_count,
            candidate_store_ids=final_target_urls,
            selection_policy=SelectionPolicy()
        )

    def _save_target_meta(self, target_data: DailyTarget):
        """
        선정된 대상 목록을 Hive 경로 정책에 맞게 JSON 파일로 저장합니다.
        """
        try:
            # Hive 스타일 디렉토리 경로 생성
            dir_path = self.path_builder.build(
                stage="target_selection", 
                status="success", 
                dt=target_data.target_date
            )
            
            # 디렉토리가 없으면 생성 (실무적 효율: 존재 여부 확인 후 생성)
            import os
            if not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
            
            file_name = f"target_meta_{target_data.batch_id}.json"
            full_path = f"{dir_path}/{file_name}"
            
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(target_data.model_dump_json(indent=2))
                
            logger.info(f"--- [Stage 0] Target metadata saved to: {full_path}")
            
        except Exception as e:
            logger.error(f"!!! [Stage 0] Failed to save target metadata: {e}")

    def _generate_batch_id(self, category_cd: str, date_str: str) -> str:
        """
        배치 식별자를 생성합니다. (YYYYMMDD_CATEGORY_UUID)
        """
        clean_date = date_str.replace("-", "")
        unique_suffix = uuid.uuid4().hex[:6].upper()
        return f"{clean_date}_{category_cd}_{unique_suffix}"
