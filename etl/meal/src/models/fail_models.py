from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional

class FailLedger(BaseModel):
    """실패 내역 기록을 위한 모델 (Fail Ledger v2)"""
    model_config = ConfigDict(populate_by_name=True)
    
    status: str = "fail"
    stage: str
    reason_code: str
    reason_detail: Optional[str] = None
    action: str  # retry, reprocess, drop
    entity_id: str
    category_cd: str
    batch_id: str = "UNKNOWN"
    failed_at: datetime = Field(default_factory=datetime.now)
    last_attempt_at: Optional[datetime] = None
    raw_path: Optional[str] = None
    retry_count: int = 0
