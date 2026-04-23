from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class RawCollectionResult(BaseModel):
    """원시 데이터 수집 결과를 담는 모델"""
    url: str
    status: str = "success"  # success, fail
    raw_content: Optional[str] = None
    http_status: Optional[int] = None
    collected_at: datetime = Field(default_factory=datetime.now)
    
    # Hive 경로 및 파일 정보
    file_path: Optional[str] = None
    file_extension: str = "html"
    
    # 실패 정보 (FailClassification 연계용)
    reason_code: Optional[str] = None
    reason_detail: Optional[str] = None
