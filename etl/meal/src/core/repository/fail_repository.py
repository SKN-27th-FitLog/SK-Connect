import logging
from typing import List, Dict, Any
from sqlalchemy import text
from src.core.repository.database import DatabaseManager
from src.core.constants import get_retry_targets

logger = logging.getLogger("core.repository")

class FailRepository:
    """
    [구현 계획 1, 3 반영] - 실패 이력 레포지토리.
    retry/reprocess 대상 선별 지원.
    """
    def __init__(self, db: DatabaseManager | None = None):
        self.db = db or DatabaseManager()

    def get_retry_targets(self, category_cd: str, platform: str) -> List[Dict[str, Any]]:
        """
        [설계안 14.5 준수] - 재시도(Retry) 대상 목록을 가져옴.
        주: 실제 구현 환경에 따라 DB의 fail_ledger 테이블이나 partition 파일을 조회.
        """
        # 시뮬레이션: DB fail_ledger 테이블이 있다고 가정
        query = get_retry_targets
        targets = []
        try:
            with self.db.get_session() as session:
                result = session.execute(text(query), {
                    "category_cd": category_cd,
                    "platform": platform
                })
                for row in result:
                    targets.append({
                        "entity_id": row.entity_id,
                        "entity_ref": row.entity_ref,
                        "retry_count": row.retry_count
                    })
        except Exception:
            # DB가 없을 경우 경고 후 빈 리스트 반환 (설계안에 따라 파일 기반 처리로 대체 가능)
            logger.debug("Fail Ledger DB table not found, skipping retry pool.")
            
        return targets
