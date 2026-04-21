import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from ..core.db_client import DBClient
from ..core.file_manager import logger, file_manager
from ..core.schema.validator import SchemaValidator
from ..core.db.sync_service import DBSyncService
from ..core.constants import LoadStatus, ProcessType

class BaseLoader:
    """
    데이터 적재의 공통 흐름을 제어하는 오케스트레이터입니다.
    (v4.0: SchemaValidator 및 DBSyncService 사용)
    """

    def __init__(self, db_client: DBClient):
        self.db = db_client
        self.validator = SchemaValidator()
        self.sync_service = DBSyncService(db_client)

    def save_with_status(self, df: pd.DataFrame, process: ProcessType, thread: str, status: LoadStatus) -> pd.DataFrame:
        """단계별 데이터 저장 공통 매서드"""
        if not df.empty:
            file_manager.save_df(df, process.value, thread, status.value)
        return df

    def record_failure(self, item: Dict[str, Any], stage: str, reason: str, original_path: Optional[str] = None) -> Dict[str, Any]:
        """실패 메타데이터 기록 (v4.0 Spec)"""
        item["fail_stage"] = stage
        item["fail_reason"] = reason
        item["original_payload_path"] = original_path or "N/A"
        item["last_attempt_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        item["retry_count"] = int(item.get("retry_count", 0)) + 1
        return item
