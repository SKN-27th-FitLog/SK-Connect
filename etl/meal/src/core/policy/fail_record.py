from datetime import datetime
from typing import Any, Dict

from src.core.policy.reason_code import ReasonCode


def build_fail_record(
    *,
    batch_id: str,
    run_attempt: int,
    stage: str,
    entity_type: str,
    entity_id: str,
    reason_code: ReasonCode | str,
    detail: str = "",
    entity_ref: Dict[str, Any] | None = None,
    retry_count: int = 0,
    data: Any = None,
    created_at: datetime | None = None,
) -> Dict[str, Any]:
    reason = reason_code.value if isinstance(reason_code, ReasonCode) else reason_code
    record = {
        "batch_id": batch_id,
        "run_attempt": run_attempt,
        "stage": stage,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "entity_ref": entity_ref or {},
        "status": "fail",
        "reason_code": reason,
        "retry_count": retry_count,
        "created_at": (created_at or datetime.now()).isoformat(),
        "detail": detail,
    }
    if data is not None:
        record["data"] = data
    return record
