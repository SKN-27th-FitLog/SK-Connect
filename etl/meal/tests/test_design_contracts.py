from datetime import datetime
from pathlib import Path
import shutil

from src.core.storage.path_builder import HivePathBuilder
from src.core.constants import (
    QUERY_FIND_MAP,
    QUERY_FIND_SHOP,
    QUERY_INSERT_CRAWLING,
    QUERY_INSERT_IMAGE,
    QUERY_INSERT_MAP,
    QUERY_INSERT_MENU,
    QUERY_INSERT_SHOP,
    QUERY_TOUCH_SHOP_CHECKED_AT,
    QUERY_FIND_SNAPSHOT_BY_DEDUP_KEY,
    QUERY_FIND_UPDATE_TARGETS,
)
from src.core.policy.fail_record import build_fail_record
from src.core.policy.reason_code import ReasonCode
from src.core.policy.resolver import Action
from src.core.registry import get_repository
from src.projects.crawl.stage0_target_selection import Stage0TargetSelection
from src.projects.crawl.stage1_raw_collection import Stage1RawCollection
from src.projects.failcheck.failcheck_service import FailcheckService
from src.projects.save.stage4_load import Stage4Load


class FakeResolver:
    def __init__(self):
        self.calls = []

    def resolve(self, reason_code, stage, retry_count):
        self.calls.append((reason_code, stage, retry_count))
        return Action.WARN


class FakeCodeRepository:
    def preload(self):
        pass

    def get_address_info(self, key):
        return {"address_cd": key, "name": f"addr-{key}"}

    def get_shop_code_name(self, code):
        return f"shop-{code}"


class FakeStoreRepository:
    def find_success_loaded_dedup_keys(self, category_cd):
        return set()

    def is_duplicated(self, target_dedup_key, existing_keys):
        return target_dedup_key in existing_keys

    def find_update_targets(self, category_cd, limit):
        return [
            {
                "address_cd": "LA02",
                "category_cd": category_cd,
                "store_id": "store-2",
                "last_checked_at": "2026-03-01T00:00:00",
                "article_url": "https://example.test/stored-shop",
            }
        ][:limit]


class FakeFailRepository:
    def get_retry_targets(self, category_cd, platform):
        return [{"address_cd": "LA01", "retry_count": 1}]


class FakeSourcePool:
    seed_file = "target.csv"

    def get_candidates(self, category_cd):
        return [{"address_cd": "LA03", "category_cd": category_cd}]


class FakeCollector:
    async def collect(self, url):
        return {"raw_content": "first"}


class CapturingSession:
    def __init__(self):
        self.params = []

    def execute(self, query, params):
        self.params.append(params)


def test_failcheck_uses_resolver_even_when_retry_limit_is_reached():
    resolver = FakeResolver()
    action = FailcheckService._resolve_action(
        {
            "reason_code": "NETWORK_ERROR",
            "stage": "raw_collection",
            "retry_count": 5,
        },
        date_str="20260427",
        resolver=resolver,
    )

    assert action == "WARN"
    assert resolver.calls == [("NETWORK_ERROR", "raw_collection", 5)]


def test_stage4_store_queries_match_current_schema():
    assert "ON CONFLICT" not in QUERY_INSERT_MAP.upper()
    assert "ON CONFLICT" not in QUERY_INSERT_SHOP.upper()
    assert "CANONICAL_URL" not in QUERY_INSERT_MAP.upper()
    assert "DEDUP_KEY" not in QUERY_INSERT_SHOP.upper()
    assert "STORE_CONTENT_HASH" not in QUERY_INSERT_SHOP.upper()
    assert "FROM MAPS" in QUERY_FIND_MAP.upper()
    assert "FROM SHOP" in QUERY_FIND_SHOP.upper()


def test_update_target_query_uses_logical_last_checked_at_from_crawling_created_at():
    query = QUERY_FIND_UPDATE_TARGETS.upper()

    assert "MAX(C.CREATED_AT)" in query
    assert "ARTICLE_URL" in query
    assert "))[1] IS NOT NULL" in query
    assert "S.LAST_CHECKED_AT" not in query


def test_snapshot_query_avoids_missing_hash_and_dedup_columns_in_current_schema():
    query = QUERY_FIND_SNAPSHOT_BY_DEDUP_KEY.upper()

    assert "STORE_CONTENT_HASH" in query
    assert "NULL::TEXT AS STORE_CONTENT_HASH" in query
    assert "S.DEDUP_KEY" not in query
    assert "M.CANONICAL_URL" not in query


def test_stage4_checked_only_writes_crawling_history_for_logical_last_checked_at():
    assert "INSERT INTO CRAWLING" in QUERY_TOUCH_SHOP_CHECKED_AT.upper()
    assert "CREATED_AT" in QUERY_TOUCH_SHOP_CHECKED_AT.upper()
    assert "NOW()" in QUERY_TOUCH_SHOP_CHECKED_AT.upper()


def test_stage4_dependent_inserts_prevent_duplicates_in_current_schema():
    menu_query = QUERY_INSERT_MENU.upper()
    image_query = QUERY_INSERT_IMAGE.upper()
    crawling_query = QUERY_INSERT_CRAWLING.upper()

    assert "WHERE NOT EXISTS" in menu_query
    assert "CAST(:NAME AS VARCHAR(100))" in menu_query
    assert "SHOP_ID = :SHOP_ID" in menu_query
    assert "NAME = CAST(:NAME AS VARCHAR(100))" in menu_query

    assert "WHERE NOT EXISTS" in image_query
    assert "CAST(:IMAGE_URL AS VARCHAR(500))" in image_query
    assert "CAST(:TABLE_NAME AS VARCHAR(20))" in image_query
    assert "TABLE_NAME = CAST(:TABLE_NAME AS VARCHAR(20))" in image_query
    assert "TABLE_ID = :TABLE_ID" in image_query
    assert "IMAGE_URL = CAST(:IMAGE_URL AS VARCHAR(500))" in image_query

    assert "WHERE NOT EXISTS" in crawling_query
    assert "CAST(:TITLE AS VARCHAR(200))" in crawling_query
    assert "CAST(:ARTICLE_URL AS VARCHAR(500))" in crawling_query
    assert "CAST(:AUTHOR AS VARCHAR(100))" in crawling_query
    assert "CAST(:KEYWORDS AS VARCHAR(100))" in crawling_query
    assert "ARTICLE_URL = CAST(:ARTICLE_URL AS VARCHAR(500))" in crawling_query
    assert "MAP_ID = :MAP_ID" in crawling_query
    assert "AUTHOR = CAST(:AUTHOR AS VARCHAR(100))" in crawling_query
    assert "CONTENT = :CONTENT" in crawling_query


def test_stage4_skips_body_load_when_record_is_unchanged():
    stage = Stage4Load(db=None, code_repository=None)
    record = {
        "store": {"entity_id": "target-1", "name": "unchanged"},
        "is_changed": False,
        "existing_store_id": "store-1",
    }

    assert stage._build_change_plan(record) == {
        "store": False,
        "menu": False,
        "review": False,
        "image": False,
        "touch_only": True,
    }


def test_stage4_truncates_crawling_varchar_fields_to_current_schema_limits():
    stage = Stage4Load(db=None, code_repository=None)
    session = CapturingSession()
    long_keywords = [f"keyword-{idx:02d}" for idx in range(30)]

    stage._load_crawling_and_reviews(
        session,
        store={
            "name": "천황식당",
            "description": "store description",
            "canonical_url": "https://www.diningcode.com/profile.php?rid=DM8NyPQ44J2J",
            "rating": 5.0,
        },
        reviews=[{
            "content": "review",
            "author": "reviewer",
            "keywords": long_keywords,
            "rating": 5.0,
        }],
        map_id="11",
        category_cd="SC01",
    )

    review_params = session.params[1]
    assert len(review_params["keywords"]) <= 100


def test_stage0_selects_retry_update_then_new_targets():
    stage = Stage0TargetSelection(
        code_repo=FakeCodeRepository(),
        store_repo=FakeStoreRepository(),
        fail_repo=FakeFailRepository(),
        source_pool=FakeSourcePool(),
        target_count=3,
        update_daily_quota=1,
        now=datetime(2026, 4, 27),
    )

    targets, _ = stage.execute("SC01", "DiningCode")

    assert [target["target_type"] for target in targets] == ["RETRY", "UPDATE", "NEW"]
    assert targets[1]["update_reason"] == "SCHEDULED_REFRESH"
    assert targets[1]["article_url"] == "https://example.test/stored-shop"
    assert targets[1]["url"] == "https://example.test/stored-shop"


def test_reference_integrity_reason_code_is_enum_backed():
    assert ReasonCode.REFERENCE_INTEGRITY_VIOLATION.value == "REFERENCE_INTEGRITY_VIOLATION"


def test_repository_lookup_returns_fresh_instances():
    first = get_repository("code_table")
    second = get_repository("code_table")

    assert first is not second


def test_raw_write_never_overwrites_existing_file():
    root = Path("test_artifacts_raw_overwrite")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir()

    try:
        stage = Stage1RawCollection(FakeCollector())
        first = stage._write_raw_file(root, "260427120000_att1_target.html", "first")
        second = stage._write_raw_file(root, "260427120000_att1_target.html", "second")

        assert first.read_text(encoding="utf-8") == "first"
        assert second.read_text(encoding="utf-8") == "second"
        assert first != second
    finally:
        shutil.rmtree(root)


def test_fail_records_use_common_jsonl_contract():
    record = build_fail_record(
        batch_id="20260427_SC01_001",
        run_attempt=2,
        stage="load",
        entity_type="store",
        entity_id="target-1",
        entity_ref={"target_id": "target-1"},
        reason_code=ReasonCode.REFERENCE_INTEGRITY_VIOLATION,
        detail="bad reference",
    )

    assert set([
        "batch_id",
        "run_attempt",
        "stage",
        "entity_type",
        "entity_id",
        "entity_ref",
        "status",
        "reason_code",
        "retry_count",
        "created_at",
        "detail",
    ]).issubset(record)
    assert record["reason_code"] == "REFERENCE_INTEGRITY_VIOLATION"


def test_hive_path_uses_category_cd_as_service_and_status_last(monkeypatch):
    monkeypatch.setattr("src.core.storage.path_builder.settings.LAKE_ROOT_PATH", "lake")
    dt = datetime(2026, 4, 28, 15, 30, 12)

    path = HivePathBuilder.build_path(
        process="raw",
        service="shop",
        category_cd="CA01",
        stage="raw_collection",
        batch_id="20260428_CA01_001",
        status="success",
        dt=dt,
    )

    assert Path(path).parts == (
        "lake",
        "crawling=raw",
        "service=CA01",
        "year=2026",
        "month=04",
        "day=28",
        "stage=raw_collection",
        "batch_id=20260428_CA01_001",
        "status=success",
    )


def test_hive_stage_base_path_matches_status_last_glob_root(monkeypatch):
    monkeypatch.setattr("src.core.storage.path_builder.settings.LAKE_ROOT_PATH", "lake")
    dt = datetime(2026, 4, 28, 15, 30, 12)

    path = HivePathBuilder.build_stage_base_path(
        process="normalized",
        service="shop",
        category_cd="CA01",
        stage="validation_normalization",
        status="success",
        dt=dt,
    )

    assert Path(path).parts == (
        "lake",
        "crawling=cleansing",
        "service=CA01",
        "year=2026",
        "month=04",
        "day=28",
        "stage=validation_normalization",
    )


def test_hive_save_path_includes_table_partition_before_status(monkeypatch):
    monkeypatch.setattr("src.core.storage.path_builder.settings.LAKE_ROOT_PATH", "lake")
    dt = datetime(2026, 4, 28, 15, 30, 12)

    path = HivePathBuilder.build_path(
        process="load",
        service="shop",
        category_cd="CA01",
        stage="load",
        batch_id="20260428_CA01_001",
        status="success",
        dt=dt,
    )

    assert Path(path).parts == (
        "lake",
        "crawling=save",
        "service=CA01",
        "year=2026",
        "month=04",
        "day=28",
        "save=shop",
        "stage=load",
        "batch_id=20260428_CA01_001",
        "status=success",
    )


def test_hive_table_csv_filename_uses_table_name_and_hhmmss():
    dt = datetime(2026, 4, 28, 15, 30, 12)

    assert HivePathBuilder.build_table_filename("shop", "csv", dt) == "shop_153012.csv"
