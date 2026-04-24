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
        category_cd: str,      # C001, C002, ...
        stage: str,            # raw_collection, candidate_parsing, validation_normalization, ...
        batch_id: str,         # YYYYMMDDHHMM
        status: str,           # success, fail, pending
        dt: datetime           # Execution Date (for year/month/day partitioning)
    ) -> str:
        """기존 Hive 스타일 전체 경로 생성"""
        return os.path.join(
            settings.LAKE_ROOT_PATH,
            f"process={process}", f"service={service}",
            f"year={dt.strftime('%Y')}", f"month={dt.strftime('%m')}", f"day={dt.strftime('%d')}",
            f"status={status}", f"category_cd={category_cd}",
            f"stage={stage}", f"batch_id={batch_id}"
        )

    @staticmethod
    def build_stage_base_path(process: str, service: str, category_cd: str, stage: str, status: str, dt) -> str:
        """batch_id를 제외한 스테이지 레벨까지의 Hive 경로 생성 (glob 검색용)"""
        return os.path.join(
            settings.LAKE_ROOT_PATH,
            f"process={process}", f"service={service}",
            f"year={dt.strftime('%Y')}", f"month={dt.strftime('%m')}", f"day={dt.strftime('%d')}",
            f"status={status}", f"category_cd={category_cd}", f"stage={stage}"
        )

    @staticmethod
    def build_filename(extension: str = "jsonl", dt: datetime = None) -> str:
        """설계안 18.2 준수 - 파일명 규격: YYMMDDHHMMmm.확장자"""
        if dt is None:
            dt = datetime.now()
        return f"{dt.strftime('%y%m%d%H%M%S')}.{extension}"
