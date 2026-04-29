import os
from datetime import datetime

from src.core.config import settings


class HivePathBuilder:
    """
    Hive-style path builder.

    Format:
    process={raw|cleansing|save|failcheck}/category_cd={category_cd}/
    year=YYYY/month=MM/day=DD/status={success|fail}/

    stage and batch_id are intentionally kept out of the directory partitions.
    They are carried by filenames and JSONL record fields instead.
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
            f"process={process_partition}",
            f"category_cd={category_cd}",
            f"year={dt.strftime('%Y')}",
            f"month={dt.strftime('%m')}",
            f"day={dt.strftime('%d')}",
        ]
        if process_partition == "save":
            parts.append(f"save={service}")
        parts.append(f"status={status}")
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
        """Build the path for a process/category/date/status partition."""
        process_partition = HivePathBuilder._normalize_process(process)
        parts = [
            settings.LAKE_ROOT_PATH,
            f"process={process_partition}",
            f"category_cd={category_cd}",
            f"year={dt.strftime('%Y')}",
            f"month={dt.strftime('%m')}",
            f"day={dt.strftime('%d')}",
        ]
        if process_partition == "save":
            parts.append(f"save={service}")
        parts.append(f"status={status}")
        return os.path.join(*parts)

    @staticmethod
    def build_filename(
        extension: str = "jsonl",
        dt: datetime = None,
        stage: str | None = None,
        batch_id: str | None = None,
        run_attempt: int | None = None,
        suffix: str | None = None,
    ) -> str:
        if dt is None:
            dt = datetime.now()
        parts = []
        if stage:
            parts.append(stage)
        if batch_id:
            parts.append(batch_id)
        parts.append(dt.strftime('%y%m%d%H%M%S'))
        if run_attempt is not None:
            parts.append(f"att{run_attempt}")
        if suffix:
            parts.append(suffix)
        return f"{'_'.join(parts)}.{extension}"

    @staticmethod
    def build_stage_file_pattern(
        process: str,
        service: str,
        category_cd: str,
        stage: str,
        status: str,
        dt: datetime,
        extension: str = "jsonl",
    ) -> str:
        base_path = HivePathBuilder.build_stage_base_path(
            process=process,
            service=service,
            category_cd=category_cd,
            stage=stage,
            status=status,
            dt=dt,
        )
        return os.path.join(base_path, f"{stage}_*.{extension}")

    @staticmethod
    def extract_batch_id_from_filename(file_path: str, stage: str) -> str:
        stem = os.path.splitext(os.path.basename(file_path))[0]
        prefix = f"{stage}_"
        if not stem.startswith(prefix):
            return ""
        parts = stem[len(prefix):].split("_")
        if len(parts) < 3:
            return ""
        return "_".join(parts[:3])

    @staticmethod
    def build_table_filename(table_name: str, extension: str = "csv", dt: datetime = None) -> str:
        if dt is None:
            dt = datetime.now()
        return f"{table_name}_{dt.strftime('%H%M%S')}.{extension}"
