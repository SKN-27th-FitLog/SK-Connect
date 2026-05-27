from datetime import datetime

from src.core.config import settings
from src.core.storage.jsonl_writer import JsonlWriter
from src.core.storage.path_builder import HivePathBuilder
from src.projects.save import save_service as save_service_module
from src.projects.save.save_service import SaveService


FIXED_DT = datetime(2026, 5, 27, 10, 30, 0)


class FixedDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return FIXED_DT


class CapturingStage4:
    def __init__(self):
        self.calls = []

    def execute(self, records, batch_id, category_cd, run_attempt=1):
        self.calls.append({
            "records": records,
            "batch_id": batch_id,
            "category_cd": category_cd,
            "run_attempt": run_attempt,
        })
        return [
            {
                "batch_id": batch_id,
                "run_attempt": run_attempt,
                "stage": "load",
                "status": "success",
                "data": record,
            }
            for record in records
        ]


class FakeCodeRepository:
    def validate_references(self, record):
        return True


def _write_stage_file(process, stage, batch_id, record):
    path = HivePathBuilder.build_path(
        process=process,
        service="shop",
        category_cd="SC01",
        stage=stage,
        batch_id=batch_id,
        status="success",
        dt=FIXED_DT,
    )
    filename = HivePathBuilder.build_filename(
        extension="jsonl",
        dt=FIXED_DT,
        stage=stage,
        batch_id=batch_id,
        run_attempt=1,
    )
    JsonlWriter.write(path, filename, [record])


def test_save_service_reads_image_validation_success_files_before_load(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "LAKE_ROOT_PATH", str(tmp_path))
    monkeypatch.setattr(save_service_module, "datetime", FixedDatetime)
    monkeypatch.setattr(save_service_module.BatchUtil, "resolve_run_attempt", lambda *args: 1)

    stage4 = CapturingStage4()
    monkeypatch.setattr(save_service_module, "get_stage", lambda name: stage4)
    monkeypatch.setattr(save_service_module, "get_repository", lambda name: FakeCodeRepository())

    batch_id = "20260527_SC01_001"
    _write_stage_file(
        process="normalized",
        stage="validation_normalization",
        batch_id=batch_id,
        record={
            "batch_id": batch_id,
            "run_attempt": 1,
            "store": {"entity_id": "store-1", "name": "식당"},
            "images": [{"url": "https://cdn.example.com/normalized.webp"}],
        },
    )
    validated_image = {
        "url": "https://cdn.example.com/validated.webp",
        "validation": {"alt_text": "식당 유사 이미지 그룹 imggrp-001 1번"},
    }
    _write_stage_file(
        process="image_validation",
        stage="image_validation",
        batch_id=batch_id,
        record={
            "batch_id": batch_id,
            "run_attempt": 1,
            "store": {"entity_id": "store-1", "name": "식당"},
            "images": [validated_image],
        },
    )

    result = SaveService.run_save("SC01")

    assert result["processed_batches"] == [batch_id]
    assert len(stage4.calls) == 1
    assert stage4.calls[0]["batch_id"] == batch_id
    assert stage4.calls[0]["records"][0]["images"] == [validated_image]
