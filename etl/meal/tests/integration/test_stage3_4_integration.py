import os
import json
import pytest
from unittest.mock import MagicMock
from src.pipeline.db_sync import DatabaseSync
from src.handlers.db_sync_handler import DbSyncHandler
from src.repositories.store_repository import StoreRepository
from src.storage.hive_path_builder import HivePathBuilder

@pytest.fixture
def mock_repo():
    repo = MagicMock(spec=StoreRepository)
    repo.save_store.return_value = 9999 # Mock Shop ID
    return repo

def test_stage3_to_stage4_integration(mock_repo, tmp_path):
    # 1. 초기 설정
    data_lake_root = str(tmp_path / "data_lake")
    path_builder = HivePathBuilder(base_root=data_lake_root)
    
    # 2. 가상의 Normalized 파일 생성 (Stage 3 결과물 모사)
    norm_dir = path_builder.build(stage="normalized", status="success")
    os.makedirs(norm_dir, exist_ok=True)
    
    norm_file_path = f"{norm_dir}/norm_test_001.jsonl"
    norm_data = {
        "source_platform": "kakao",
        "source_internal_id": "ks_123",
        "name": "원본 상호명",
        "normalized_name": "정규화 상호명",
        "address": "원본 주소",
        "normalized_address": "정규화 주소",
        "canonical_url": "https://restaurant.com/2",
        "category_cd": "CA01",
        "latitude": 37.1234,
        "longitude": 127.1234,
        "dedup_key": "key_123",
        "dedup_rule_version": "v1",
        "entity_completeness": 1.0,
        "extracted_at": "2026-04-23T12:00:00"
    }
    with open(norm_file_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(norm_data) + "\n")

    # 3. Handler를 통해 Stage 4 실행
    db_sync_stage = DatabaseSync(repository=mock_repo)
    handler = DbSyncHandler(db_sync_stage=db_sync_stage)
    
    handler_res = handler.handle(normalized_file_paths=[norm_file_path])
    
    # 4. 검증
    assert handler_res["success_count"] == 1
    assert handler_res["details"][0]["shop_id"] == 9999
    
    # Repository 호출 시 데이터 매핑이 올바르게 되었는지 확인
    # 특히 'normalized_name'과 'normalized_address'가 DB 필드로 들어갔는지 확인
    called_data = mock_repo.save_store.call_args[0][0]
    assert called_data["name"] == "정규화 상호명"
    assert called_data["address_detail"] == "정규화 주소"
    assert called_data["latitude"] == 37.1234
    
    print(f"\n--- Stage 3-4 Integration Success: Data synced to DB with Shop ID {handler_res['details'][0]['shop_id']}")
