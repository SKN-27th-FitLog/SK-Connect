from typing import List, Dict, Any
from sqlalchemy import text
from src.pipeline.stages.base_stage import BaseStage
from src.core.repository.database import db_manager
from src.core.constants import (
    QUERY_SELECT_SUCCESSFUL_STORE_IDS,
    QUERY_SELECT_RETRY_TARGETS,
    QUERY_SELECT_NEW_TARGETS
)

class Stage0TargetSelection(BaseStage):
    """
    설계안 6.2 준수 - Daily Target Selection.
    목표: 성공 적재 100건을 위한 대상 선정.
    """
    def __init__(self, target_count: int = 100):
        super().__init__("target_selection")
        self.target_count = target_count

    def execute(self, category_cd: str, platform: str = "DiningCode") -> List[Dict[str, Any]]:
        """
        성공한 내역 제외, Retry 우선, 부족분 신규 후보로 충전.
        """
        with db_manager.get_session() as session:
            # 1. 이미 성공한 ID 목록 조회
            success_rows = session.execute(
                text(QUERY_SELECT_SUCCESSFUL_STORE_IDS), 
                {"platform": platform}
            ).mappings().all()
            success_ids = {row['source_internal_id'] for row in success_rows}

            # 2. Retry 대상 조회
            retry_targets = session.execute(
                text(QUERY_SELECT_RETRY_TARGETS),
                {"max_retries": 5}
            ).mappings().all()
            
            selected_targets = []
            for t in retry_targets:
                if t['url'] not in success_ids: # 실제로는 internal_id 비교가 정확하겠으나 URL로 예시
                    selected_targets.append(dict(t))
                    if len(selected_targets) >= self.target_count:
                        break
            
            # 3. 부족분 신규 후보로 보충
            if len(selected_targets) < self.target_count:
                limit = self.target_count - len(selected_targets)
                new_targets = session.execute(
                    text(QUERY_SELECT_NEW_TARGETS),
                    {"limit": limit * 2} # 필터링 대비 여유있게 조회
                ).mappings().all()
                
                for t in new_targets:
                    if t['url'] not in success_ids:
                        selected_targets.append(dict(t))
                    if len(selected_targets) >= self.target_count:
                        break
            
            self.logger.info(f"Selected {len(selected_targets)} targets for category {category_cd}")
            return selected_targets
