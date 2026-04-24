import logging
from typing import List, Dict, Any
from datetime import datetime

from src.core.base_stage import BaseStage
from src.core.storage.path_builder import HivePathBuilder
from src.core.storage.jsonl_writer import JsonlWriter
from src.core.policy.resolver import PolicyResolver, policy_resolver, Action
from src.core.policy.reason_code import ReasonCode

class Stage5FailClassification(BaseStage):
    """
    [설계안 19 일치] - Fail Classification Stage.
    실패 사유를 분류하고 Fail Ledger(JSONL)에 기록.
    원칙: Fail Ledger는 DB가 아닌 JSONL 파일로 관리
    """
    NAME = "fail_classification"

    def __init__(self, resolver: PolicyResolver = policy_resolver):
        super().__init__(self.NAME)
        self.policy_resolver = resolver

    def execute(self, shard_results: List[Dict[str, Any]], batch_id: str, category_cd: str) -> List[Dict[str, Any]]:
        failures = []
        now = datetime.now()

        for res in shard_results:
            if res.get("status") == "fail":
                reason_code_str = res.get("reason_code", "UNKNOWN_ERROR")
                reason_code = ReasonCode[reason_code_str] if reason_code_str in ReasonCode.__members__ else ReasonCode.UNKNOWN_ERROR
                
                failure_entry = {
                    "entity_id": res.get("entity_id"),
                    "entity_ref": res.get("entity_ref"),
                    "reason_code": reason_code.name,
                    "detail": res.get("detail", ""),
                    "retry_allowed": self.policy_resolver.resolve(reason_code, stage=self.NAME) == Action.RETRY,
                    "failed_at": res.get("collected_at", now.isoformat())
                }
                failures.append(failure_entry)

        if failures:
            fail_ledger_path = HivePathBuilder.build_path(
                process="fail_ledger", service="shop", category_cd=category_cd,
                stage="all", batch_id=batch_id, status="failed", dt=now
            )
            filename = HivePathBuilder.build_filename(extension="jsonl", dt=now)
            JsonlWriter.write(fail_ledger_path, filename, failures)
            
            self.logger.info(f"Classified {len(failures)} failures to JSONL for batch {batch_id}")

        return failures
