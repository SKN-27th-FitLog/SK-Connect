import os
from datetime import datetime

from src.core.config import settings


class HivePathBuilder:
    """
    Hive-style path builder.

    Format:
    crawling={raw|cleansing|save|failcheck}/service={category_cd}/
    year=YYYY/month=MM/day=DD/stage={stage_name}/batch_id={batch_id}/status={success|fail}/
    """

    PROCESS_ALIASES = {
        "candidate": "cleansing",
        "normalized": "cleansing",
        "load": "save",
        "retry": "failcheck",
        "reprocess": "failcheck",
        "dropped": "failcheck",
        "warning": "failcheck",
    }

    @staticmethod
    def _normalize_process(process: str) -> str:
        return HivePathBuilder.PROCESS_ALIASES.get(process, process)

    @staticmethod
    def build_path(
        process: str,
        service: str,
        category_cd: str,
        stage: str,
        batch_id: str,
        status: str,
        dt: datetime,
    ) -> str:
        """Build a full Hive path for a batch/status partition."""
        process_partition = HivePathBuilder._normalize_process(process)
        parts = [
            settings.LAKE_ROOT_PATH,
            f"crawling={process_partition}",
            f"service={category_cd}",
            f"year={dt.strftime('%Y')}",
            f"month={dt.strftime('%m')}",
            f"day={dt.strftime('%d')}",
        ]
        if process_partition == "save":
            parts.append(f"save={service}")
        parts.extend([
            f"stage={stage}",
            f"batch_id={batch_id}",
            f"status={status}",
        ])
        return os.path.join(*parts)

    @staticmethod
    def build_stage_base_path(
        process: str,
        service: str,
        category_cd: str,
        stage: str,
        status: str,
        dt: datetime,
    ) -> str:
        """Build the path prefix up to stage; append batch/status for glob reads."""
        process_partition = HivePathBuilder._normalize_process(process)
        parts = [
            settings.LAKE_ROOT_PATH,
            f"crawling={process_partition}",
            f"service={category_cd}",
            f"year={dt.strftime('%Y')}",
            f"month={dt.strftime('%m')}",
            f"day={dt.strftime('%d')}",
        ]
        if process_partition == "save":
            parts.append(f"save={service}")
        parts.append(
            f"stage={stage}",
        )
        return os.path.join(*parts)

    @staticmethod
    def build_filename(extension: str = "jsonl", dt: datetime = None) -> str:
        if dt is None:
            dt = datetime.now()
        return f"{dt.strftime('%y%m%d%H%M%S')}.{extension}"

    @staticmethod
    def build_table_filename(table_name: str, extension: str = "csv", dt: datetime = None) -> str:
        if dt is None:
            dt = datetime.now()
        return f"{table_name}_{dt.strftime('%H%M%S')}.{extension}"
