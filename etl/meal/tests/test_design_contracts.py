from datetime import datetime
from pathlib import Path
import shutil

from src.core.constants import QUERY_UPSERT_MAP, QUERY_UPSERT_SHOP
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


def test_upsert_queries_are_real_upserts():
    assert "ON CONFLICT" in QUERY_UPSERT_MAP.upper()
    assert "DO UPDATE" in QUERY_UPSERT_MAP.upper()
    assert "ON CONFLICT" in QUERY_UPSERT_SHOP.upper()
    assert "DO UPDATE" in QUERY_UPSERT_SHOP.upper()


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
