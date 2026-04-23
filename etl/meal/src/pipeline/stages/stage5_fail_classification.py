from typing import List, Dict, Any
from sqlalchemy import text
from src.pipeline.stages.base_stage import BaseStage
from src.core.policy.resolver import PolicyResolver, policy_resolver
from src.core.policy.reason_code import ReasonCode
from src.core.storage.path_builder import HivePathBuilder
from src.core.storage.jsonl_writer import JsonlWriter
from src.core.repository.database import db_manager
from src.core.constants import QUERY_INSERT_FAIL_LEDGER
from src.core.models.models import FailLedgerModel
from datetime import datetime

class Stage5FailClassification(BaseStage):
    """
    설계안 2.2, 14장 준수 - Fail Classification / Retry Scheduling Stage.
    실패 원인을 분석하고 Resolver를 통해 후속 Action을 결정하여 기록.
    """
    def __init__(self, resolver: PolicyResolver = policy_resolver):
        super().__init__("fail_classification")
        self.resolver = resolver

    def execute(self, all_failures: List[Dict[str, Any]], batch_id: str, category_cd: str) -> List[Dict[str, Any]]:
        """
        모든 단계의 실패 목록을 받아 Action 결정 및 Ledger 기록.
        """
        classified_results = []
        now = datetime.now()
        
        for fail in all_failures:
            reason_str = fail.get("reason_code", "UNKNOWN_ERROR")
            try:
                reason_code = ReasonCode[reason_str]
            except KeyError:
                reason_code = ReasonCode.UNKNOWN_ERROR
            
            # 1. Resolver를 통한 Action 결정 (설계안 7.4)
            action = self.resolver.resolve(
                reason_code=reason_code,
                stage=fail.get("stage", "unknown"),
                retry_count=fail.get("retry_count", 0)
            )
            
            # 2. Fail Ledger 모델 생성
            ledger_entry = FailLedgerModel(
                batch_id=batch_id,
                stage=fail.get("stage", "unknown"),
                entity_type=fail.get("entity_type", "unknown"),
                entity_id=fail.get("entity_id", "unknown"),
                entity_ref=fail.get("entity_ref", {}),
                reason_code=reason_code.name,
                action=action.name,
                detail=fail.get("detail", ""),
                retry_count=fail.get("retry_count", 0)
            )
            
            # 3. DB 기록 (설계안 14.1)
            try:
                with db_manager.get_session() as session:
                    session.execute(text(QUERY_INSERT_FAIL_LEDGER), ledger_entry.model_dump(mode='json'))
                    session.commit()
            except Exception as e:
                self.logger.error(f"Failed to write to DB Fail Ledger: {str(e)}")
            
            classified_results.append(ledger_entry.model_dump())

        # 4. JSONL 파일로 기록 (설계안 4.1)
        fail_ledger_path = HivePathBuilder.build_path(
            process="fail_ledger", service="shop", category_cd=category_cd,
            stage=self.stage_name, batch_id=batch_id, status="success", dt=now
        )
        filename = HivePathBuilder.build_filename(extension="jsonl", dt=now)
        JsonlWriter.write(fail_ledger_path, filename, classified_results)
        
        self.logger.info(f"Classified {len(classified_results)} failures for batch {batch_id}")
        return classified_results
