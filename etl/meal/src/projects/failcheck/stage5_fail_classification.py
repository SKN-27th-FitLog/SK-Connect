import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

from src.core.base_stage import BaseStage
from src.core.policy.resolver import Action, PolicyResolver, create_policy_resolver


class Stage5FailClassification(BaseStage):
    """
    설계안 2절 / Stage 5 - Fail Classification.
    실패 레코드를 받아 action별 버킷으로 분류하여 반환한다.
    파일 I/O와 Dispatcher 호출은 FailcheckService가 담당한다.
    """
    NAME = "fail_classification"

    def __init__(self, resolver: PolicyResolver | None = None):
        super().__init__(self.NAME)
        self.policy_resolver = resolver or create_policy_resolver()

    def execute(self, records: List[Dict[str, Any]], date_str: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        records: 모든 fail JSONL에서 읽어온 실패 레코드 목록
        date_str: 오늘 날짜 문자열 (YYYYMMDD) — 당일 재시도 중복 방지에 사용
        반환: {"RETRY": [...], "REPROCESS": [...], "DROP": [...], "WARN": [...]}
        """
        now = datetime.now()
        buckets: Dict[str, List[Dict[str, Any]]] = {
            "RETRY": [],
            "REPROCESS": [],
            "DROP": [],
            "WARN": [],
        }

        for record in records:
            if record.get("last_retry_date") == date_str:
                self.logger.info(f"Skipping same-day retry: {record.get('entity_id')}")
                continue

            reason_code = record.get("reason_code", "UNKNOWN_ERROR")
            stage_val = record.get("stage", "unknown")
            retry_count = record.get("retry_count", 0)

            action = self.policy_resolver.resolve(reason_code, stage_val, retry_count)
            action_name = action.name if isinstance(action, Action) else str(action)

            retry_available_date = (now + timedelta(days=1)).strftime("%Y-%m-%d") if action == Action.RETRY else None
            enriched = {
                **record,
                "action_taken": action_name,
                "retry_available_date": retry_available_date,
            }

            buckets.get(action_name, buckets["WARN"]).append(enriched)

        self.logger.info(
            f"Classified {len(records)} records → "
            f"RETRY:{len(buckets['RETRY'])} REPROCESS:{len(buckets['REPROCESS'])} "
            f"DROP:{len(buckets['DROP'])} WARN:{len(buckets['WARN'])}"
        )
        return buckets
