import os
from datetime import datetime
from src.core.config import settings

class HivePathBuilder:
    """
    설계안 18.1 준수 - Hive 스타일 경로 생성기.
    형식: process={raw|candidate|...}/service={shop|...}/year=YYYY/month=MM/day=DD/status={success|fail}/category_cd={CAxx}/stage={stage_name}/batch_id={batch_id}/
    """
    
    @staticmethod
    def build_path(
        process: str,          # raw, candidate, normalized, fail_ledger, metrics
        service: str,          # shop, menu, review, image
        category_cd: str,
        stage: str,
        batch_id: str,
        status: str = "success",
        base_path: str = settings.LAKE_ROOT_PATH,
        dt: datetime = None
    ) -> str:
        if dt is None:
            dt = datetime.now()
            
        path = os.path.join(
            base_path,
            f"process={process}",
            f"service={service}",
            f"year={dt.strftime('%Y')}",
            f"month={dt.strftime('%m')}",
            f"day={dt.strftime('%d')}",
            f"status={status}",
            f"category_cd={category_cd}",
            f"stage={stage}",
            f"batch_id={batch_id}"
        )
        return path

    @staticmethod
    def build_filename(extension: str = "jsonl", dt: datetime = None) -> str:
        """설계안 18.2 준수 - 파일명 규격: YYMMDDHHMMmm.확장자"""
        if dt is None:
            dt = datetime.now()
        return f"{dt.strftime('%y%m%d%H%M%S')}.{extension}"
