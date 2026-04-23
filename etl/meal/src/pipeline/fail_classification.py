from datetime import datetime
from ..core.file_manager import logger
from ..core.fail_resolver import FailResolver
from ..db.models.fail_models import FailLedger

class FailClassification:
    """
    Stage 5: Fail Classification
    실패한 데이터의 원인을 분석하고 후속 action(retry/drop/reprocess)을 결정합니다.
    (v4 Stateless: DB에 적재하지 않고 로그로만 관리)
    """
    
    def __init__(self, db_client=None):
        self.db = db_client
        self.resolver = FailResolver()

    def classify_and_log(self, 
                         stage: str, 
                         reason_code: str, 
                         entity_id: str, 
                         category_cd: str,
                         batch_id: str = "UNKNOWN",
                         retry_count: int = 0,
                         reason_detail: str = None,
                         raw_path: str = None) -> FailLedger:
        """
        실패 데이터를 분류하고 FailLedger 객체(로그용)를 생성합니다.
        """
        # 1. 정책 기반 Action 결정
        action = self.resolver.resolve(reason_code, retry_count)
        
        # 2. FailLedger 객체 생성 (나중에 파일로 저장하거나 로그로 활용)
        ledger = FailLedger(
            stage=stage,
            reason_code=reason_code,
            reason_detail=reason_detail,
            action=action,
            entity_id=entity_id,
            category_cd=category_cd,
            batch_id=batch_id,
            failed_at=datetime.now(),
            raw_path=raw_path,
            retry_count=retry_count,
            last_attempt_at=datetime.now()
        )
        
        # 3. 로그 기록 (Stateless 관리의 핵심)
        logger.warning(f"!!! [Stage 5] FAIL_DETECTED: Stage={stage}, ID={entity_id}, Code={reason_code}, Action={action}")
        if reason_detail:
            logger.warning(f"    Detail: {reason_detail}")
        
        return ledger
