from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from src.core.config import settings
from src.core.registry import STAGE_IMAGE_VALIDATION, get_stage
from src.core.storage.jsonl_writer import JsonlWriter
from src.core.storage.path_builder import HivePathBuilder
from src.projects.image_validation.image_validation_service import ImageValidationService
from src.projects.image_validation.stage_image_validation import StageImageValidation


def test_image_validation_service_reads_normalized_and_writes_image_validation(monkeypatch):
    with _make_lake_root() as lake_root:
        monkeypatch.setattr(settings, "LAKE_ROOT_PATH", str(lake_root))
        dt = datetime(2026, 5, 27, 10, 0, 0)
        batch_id = "20260527_SC01_001"
        normalized_path = HivePathBuilder.build_path(
            process="normalized",
            service="shop",
            category_cd="SC01",
            stage="validation_normalization",
            batch_id=batch_id,
            status="success",
            dt=dt,
        )
        filename = HivePathBuilder.build_filename(
            "jsonl",
            dt,
            stage="validation_normalization",
            batch_id=batch_id,
            run_attempt=3,
        )
        JsonlWriter.write(
            normalized_path,
            filename,
            [
                {
                    "batch_id": batch_id,
                    "run_attempt": 3,
                    "entity_id": "store-1",
                    "store": {"name": "Store"},
                    "images": [{"url": "a"}, {"url": "b"}, {"url": "c"}],
                }
            ],
        )

        service = ImageValidationService(
            vector_provider=lambda url: [1.0, 0.0],
            now_provider=lambda: dt,
            model_version="fake",
        )

        result = service.run_image_validation("SC01")

        assert result["processed_batches"] == [batch_id]
        files = list(lake_root.rglob("image_validation_*.jsonl"))
        assert len(files) == 1
        assert "process=cleaning" in str(files[0])
        saved = JsonlWriter.read(str(files[0]))
        assert len(saved) == 1
        assert saved[0]["batch_id"] == batch_id
        assert saved[0]["run_attempt"] == 3
        assert saved[0]["stage"] == "image_validation"
        assert [image["url"] for image in saved[0]["images"]] == ["a", "b", "c"]


def test_image_validation_service_uses_one_run_scoped_cache(monkeypatch):
    with _make_lake_root() as lake_root:
        monkeypatch.setattr(settings, "LAKE_ROOT_PATH", str(lake_root))
        dt = datetime(2026, 5, 27, 10, 0, 0)
        batch_id = "20260527_SC01_001"
        normalized_path = HivePathBuilder.build_path(
            process="normalized",
            service="shop",
            category_cd="SC01",
            stage="validation_normalization",
            batch_id=batch_id,
            status="success",
            dt=dt,
        )
        filename = HivePathBuilder.build_filename(
            "jsonl",
            dt,
            stage="validation_normalization",
            batch_id=batch_id,
            run_attempt=1,
        )
        JsonlWriter.write(
            normalized_path,
            filename,
            [
                {
                    "batch_id": batch_id,
                    "run_attempt": 1,
                    "entity_id": "store-1",
                    "images": [{"url": "same"}, {"url": "same"}],
                }
            ],
        )
        calls = []

        def vector_provider(url):
            calls.append(url)
            return [1.0, 0.0]

        service = ImageValidationService(
            vector_provider=vector_provider,
            now_provider=lambda: dt,
            model_version="fake",
        )

        service.run_image_validation("SC01")

        assert calls == ["same"]


def test_image_validation_registry_and_process_alias_are_registered():
    assert STAGE_IMAGE_VALIDATION == "image_validation"
    assert isinstance(get_stage(STAGE_IMAGE_VALIDATION, vector_provider=lambda url: [1.0]), StageImageValidation)
    assert HivePathBuilder._normalize_process("image_validation") == "cleaning"


@contextmanager
def _make_lake_root():
    workspace_root = Path(__file__).resolve().parents[3]
    with TemporaryDirectory(prefix=".pytest-image-validation-", dir=workspace_root) as lake_root:
        yield Path(lake_root)
