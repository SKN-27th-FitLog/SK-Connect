from datetime import datetime
from .base_repository import BaseRepository
from ..queries.fail_queries import INSERT_FAIL_LEDGER
from ..models.fail_models import FailLedger

class FailRepository(BaseRepository):
    """
    실패 내역(Fail Ledger) 기록을 담당하는 리포지토리입니다.
    """

    def save_fail_ledger(self, ledger: FailLedger):
        """
        실패 내역을 DB에 UPSERT 합니다.
        """
        params = (
            ledger.entity_id,
            ledger.category_cd,
            ledger.batch_id,
            ledger.stage,
            ledger.reason_code,
            ledger.reason_detail,
            ledger.action,
            "fail", # status
            ledger.retry_count,
            ledger.last_attempt_at
        )
        
        try:
            self.execute(INSERT_FAIL_LEDGER, params)
        except Exception as e:
            # 실패 기록 자체가 실패할 경우 로그로만 남김 (무한 루프 방지)
            from ...core.file_manager import logger
            logger.error(f"!!! [FailRepository] Critical failure while saving ledger: {e}")
            raise
