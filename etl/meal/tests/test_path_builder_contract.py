from datetime import datetime

from src.core.config import settings
from src.core.storage.path_builder import HivePathBuilder


def test_build_path_uses_restaurant_category_and_shop_partition(monkeypatch):
    monkeypatch.setattr(settings, "LAKE_ROOT_PATH", "lake")
    dt = datetime(2026, 4, 28, 15, 30, 12)

    path = HivePathBuilder.build_path(
        process="normalized",
        service="shop",
        category_cd="SC01",
        stage="validation_normalization",
        batch_id="20260428_SC01_001",
        status="success",
        dt=dt,
    )

    assert path == (
        "lake\\process=cleaning\\category_cd=CA01\\shop_cd=SC01\\year=2026\\month=04\\day=28\\status=success"
    )
    assert "stage=" not in path
    assert "batch_id=" not in path
    assert "crawling=" not in path
    assert "service=" not in path


def test_build_save_path_keeps_table_partition_without_stage_or_batch(monkeypatch):
    monkeypatch.setattr(settings, "LAKE_ROOT_PATH", "lake")
    dt = datetime(2026, 4, 28, 15, 30, 12)

    path = HivePathBuilder.build_path(
        process="load",
        service="shop",
        category_cd="SC01",
        stage="load",
        batch_id="20260428_SC01_001",
        status="success",
        dt=dt,
    )

    assert path == (
        "lake\\process=save\\category_cd=CA01\\shop_cd=SC01\\year=2026\\month=04\\day=28\\save=shop\\status=success"
    )


def test_build_filename_can_include_stage_batch_and_attempt():
    dt = datetime(2026, 4, 28, 15, 30, 12)

    filename = HivePathBuilder.build_filename(
        extension="jsonl",
        dt=dt,
        stage="validation_normalization",
        batch_id="20260428_CA01_001",
        run_attempt=2,
    )

    assert filename == "validation_normalization_20260428_CA01_001_260428153012_att2.jsonl"
