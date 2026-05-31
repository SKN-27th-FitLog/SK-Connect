import glob
import logging
import os
from collections.abc import Callable
from datetime import datetime
from typing import Any

from src.core.policy.fail_record import build_fail_record
from src.core.policy.reason_code import ReasonCode
from src.core.storage.jsonl_writer import JsonlWriter
from src.core.storage.path_builder import HivePathBuilder
from src.projects.image_validation.stage_image_validation import StageImageValidation
from src.services.image_validation.cache import ImageVectorCache
from src.services.image_validation.grouping import (
    DEFAULT_IMAGE_SIMILARITY_THRESHOLD,
    DEFAULT_MIN_SIMILAR_IMAGE_GROUP_SIZE,
)
from src.services.image_validation.vectorizer import ClipImageVectorizer

logger = logging.getLogger("image_validation_project")


class ImageValidationService:
    def __init__(
        self,
        vector_provider: Callable[[str], Any] | None = None,
        similarity_threshold: float = DEFAULT_IMAGE_SIMILARITY_THRESHOLD,
        min_group_size: int = DEFAULT_MIN_SIMILAR_IMAGE_GROUP_SIZE,
        model_version: str | None = None,
        now_provider: Callable[[], datetime] | None = None,
    ):
        self.vector_provider = vector_provider
        self.similarity_threshold = similarity_threshold
        self.min_group_size = min_group_size
        self.model_version = model_version
        self.now_provider = now_provider or datetime.now

    def run_image_validation(self, category_cd: str) -> dict[str, list[str]]:
        logger.info(f"--- Starting IMAGE VALIDATION Project: {category_cd} ---")
        dt = self.now_provider()
        normalized_files = self._find_normalized_success_files(category_cd, dt)
        if not normalized_files:
            logger.info("No normalized data found for image validation.")
            return {"processed_batches": []}

        vector_provider, model_version = self._build_run_scoped_vector_provider()
        stage = StageImageValidation(
            vector_provider=vector_provider,
            similarity_threshold=self.similarity_threshold,
            min_group_size=self.min_group_size,
            model_version=model_version,
        )

        files_by_batch = self._group_files_by_batch(normalized_files)
        processed_batches: list[str] = []
        for batch_id, batch_files in files_by_batch.items():
            records = self._read_records(batch_files)
            if not records:
                continue

            successes, failures = self._validate_batch_records(
                stage=stage,
                records=records,
                batch_id=batch_id,
                category_cd=category_cd,
                dt=dt,
            )
            run_attempt = self._resolve_run_attempt(records)

            if successes:
                self._write_records(
                    records=successes,
                    process="image_validation",
                    category_cd=category_cd,
                    batch_id=batch_id,
                    run_attempt=run_attempt,
                    status="success",
                    dt=dt,
                )
            if failures:
                self._write_records(
                    records=failures,
                    process="image_validation",
                    category_cd=category_cd,
                    batch_id=batch_id,
                    run_attempt=run_attempt,
                    status="fail",
                    dt=dt,
                    suffix="fail",
                )

            processed_batches.append(batch_id)

        logger.info("--- IMAGE VALIDATION Project Finished ---")
        return {"processed_batches": processed_batches}

    def _find_normalized_success_files(self, category_cd: str, dt: datetime) -> list[str]:
        base_path = HivePathBuilder.build_stage_base_path(
            process="normalized",
            service="shop",
            category_cd=category_cd,
            stage="validation_normalization",
            status="success",
            dt=dt,
        )
        return glob.glob(os.path.join(base_path, "validation_normalization_*.jsonl"))

    def _build_run_scoped_vector_provider(self) -> tuple[Callable[[str], Any], str]:
        raw_provider = self.vector_provider
        model_version = self.model_version

        if raw_provider is None:
            vectorizer = ClipImageVectorizer()
            raw_provider = vectorizer.vectorize
            model_version = model_version or vectorizer.model_version

        cache = ImageVectorCache(raw_provider)
        return cache.get, model_version or "custom"

    def _group_files_by_batch(self, files: list[str]) -> dict[str, list[str]]:
        files_by_batch: dict[str, list[str]] = {}
        for file_path in files:
            batch_id = HivePathBuilder.extract_batch_id_from_filename(
                file_path,
                "validation_normalization",
            )
            if batch_id:
                files_by_batch.setdefault(batch_id, []).append(file_path)
        return files_by_batch

    def _read_records(self, files: list[str]) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for file_path in files:
            records.extend(JsonlWriter.read(file_path))
        return records

    def _validate_batch_records(
        self,
        stage: StageImageValidation,
        records: list[dict[str, Any]],
        batch_id: str,
        category_cd: str,
        dt: datetime,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        successes: list[dict[str, Any]] = []
        failures: list[dict[str, Any]] = []

        for record in records:
            try:
                run_attempt = self._resolve_run_attempt([record])
                successes.extend(
                    stage.execute(
                        [record],
                        batch_id=batch_id,
                        category_cd=category_cd,
                        run_attempt=run_attempt,
                    )
                )
            except Exception as exc:
                failures.append(
                    self._build_fail_record(
                        record=record,
                        batch_id=batch_id,
                        stage=stage.NAME,
                        detail=str(exc),
                        created_at=dt,
                    )
                )
        return successes, failures

    def _write_records(
        self,
        records: list[dict[str, Any]],
        process: str,
        category_cd: str,
        batch_id: str,
        run_attempt: int,
        status: str,
        dt: datetime,
        suffix: str | None = None,
    ) -> None:
        output_path = HivePathBuilder.build_path(
            process=process,
            service="shop",
            category_cd=category_cd,
            stage=StageImageValidation.NAME,
            batch_id=batch_id,
            status=status,
            dt=dt,
        )
        filename = HivePathBuilder.build_filename(
            extension="jsonl",
            dt=dt,
            stage=StageImageValidation.NAME,
            batch_id=batch_id,
            run_attempt=run_attempt,
            suffix=suffix,
        )
        JsonlWriter.write(output_path, filename, records)

    def _resolve_run_attempt(self, records: list[dict[str, Any]]) -> int:
        for record in records:
            if isinstance(record, dict) and record.get("run_attempt") is not None:
                return int(record["run_attempt"])
        return 1

    def _build_fail_record(
        self,
        record: Any,
        batch_id: str,
        stage: str,
        detail: str,
        created_at: datetime,
    ) -> dict[str, Any]:
        source = record if isinstance(record, dict) else {}
        store = source.get("store", {}) if isinstance(source.get("store", {}), dict) else {}
        return build_fail_record(
            batch_id=batch_id,
            run_attempt=self._resolve_run_attempt([source]),
            stage=stage,
            entity_type="store",
            entity_id=store.get("entity_id", source.get("entity_id", "unknown")),
            entity_ref=store.get("entity_ref", source.get("entity_ref", {})),
            reason_code=ReasonCode.INTERNAL_PIPELINE_ERROR,
            retry_count=source.get("retry_count", 0) + 1,
            detail=detail,
            data=record,
            created_at=created_at,
        )
