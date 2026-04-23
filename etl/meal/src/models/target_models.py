from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import date

class SelectionPolicy(BaseModel):
    """수집 대상 선정 정책 모델"""
    exclude_success_loaded_store: bool = True
    allow_retry_by_reason_code: bool = True
    max_retry_limit: int = 5

class DailyTarget(BaseModel):
    """일일 수집 대상 정보 모델 (Stage 0 출력)"""
    batch_id: str
    category_cd: str
    target_date: date
    target_count: int = 100
    candidate_store_ids: List[str]
    selection_policy: SelectionPolicy
