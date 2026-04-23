from datetime import datetime
from ..core.file_manager import logger
from ..core.fail_resolver import FailResolver
from ..db.models.fail_models import FailLedger
from ..db.repositories.fail_repository import FailRepository

class FailClassification:
    """
    Stage 5: Fail Classification
    실패한 데이터의 원인을 분석하고 후속 action(retry/drop/reprocess)을 결정하여
    Fail Ledger를 생성하고 영속화합니다.
    """
    
    def __init__(self, db_client=None):
        self.db = db_client
        self.resolver = FailResolver()
        # DB 클라이언트가 있으면 리포지토리 활성화
        self.repository = FailRepository(db_client) if db_client else None

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
        실패 데이터를 분류하고 FailLedger 객체를 생성하여 DB에 저장합니다.
        """
        # 1. 정책 기반 Action 결정
        action = self.resolver.resolve(reason_code, retry_count)
        
        # 2. FailLedger 객체 생성
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
        
        logger.warning(f"--- [Stage 5] Fail Classified: ID={entity_id}, Code={reason_code}, Action={action}")
        
        # 3. 영속화 (Repository 활용)
        if self.repository:
            try:
                self.repository.save_fail_ledger(ledger)
                logger.info(f"--- [Stage 5] Fail Ledger persisted to DB for ID: {entity_id}")
            except Exception as e:
                # DB 저장 실패 시에도 프로그램은 계속 진행 (로그로만 남김)
                logger.error(f"!!! [Stage 5] Failed to persist fail ledger: {e}")
        else:
            logger.info("--- [Stage 5] No repository available. Skipping DB persistence.")
        
        return ledger
