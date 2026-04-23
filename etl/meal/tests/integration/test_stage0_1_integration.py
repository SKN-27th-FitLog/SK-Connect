import os
import json
import pytest
from unittest.mock import MagicMock, patch
from datetime import date

from src.pipeline.target_selection import TargetSelection
from src.handlers.collect_raw_handler import CollectRawHandler
from src.core.storage.hive_path_builder import HivePathBuilder

@pytest.fixture
def mock_db():
    db = MagicMock()
    # TargetSelection에 필요한 리턴값 설정 (두 개의 URL 후보)
    db.execute_query.side_effect = [
        [], # get_retry_targets
        [
            {"canonical_url": "https://restaurant.com/1"},
            {"canonical_url": "https://restaurant.com/2"}
        ] # get_new_candidates
    ]
    return db

@pytest.fixture
def mock_collector():
    collector = MagicMock()
    collector.collect.return_value = {
        "status": "success",
        "raw_content": "<html><body>Mock Restaurant</body></html>",
        "http_status": 200
    }
    return collector

def test_stage0_to_stage1_integration(mock_db, mock_collector, tmp_path):
    # 1. 초기 설정 (임시 경로 사용)
    data_lake_root = str(tmp_path / "data_lake")
    path_builder = HivePathBuilder(base_root=data_lake_root)
    
    # [Phase 1] Stage 0 실행 및 Meta 파일 생성
    selector = TargetSelection(db_client=mock_db, resolver=None, path_builder=path_builder)
    target_res = selector.run(category_cd="CA01", target_count=2)
    
    batch_id = target_res["batch_id"]
    # 저장된 메타 파일 확인
    meta_dir = path_builder.build(stage="target_selection", status="success", dt=date.today())
    meta_file = f"{meta_dir}/target_meta_{batch_id}.json"
    
    assert os.path.exists(meta_file), "Target meta file should be created."
    
    # [Phase 2] Handler를 통해 Stage 1 실행
    handler = CollectRawHandler()
    # 핸들러 내부의 raw_collector의 path_builder와 collector를 교체 (DI)
    handler.raw_collector.path_builder = path_builder
    handler.raw_collector.collector = mock_collector
    
    handler_res = handler.handle(meta_file_path=meta_file)
    
    # [Phase 3] 최종 검증
    assert handler_res["success_count"] == 2
    assert handler_res["total_count"] == 2
    
    # Raw 파일들이 생성되었는지 전수 검증
    raw_dir = path_builder.build(stage="raw", status="success", service="shop")
    raw_files = [f for f in os.listdir(raw_dir) if f.endswith(".html")]
    
    assert len(raw_files) == 2, "Two raw collection files should be created in the data lake."
    print(f"\n--- Integration Success: {len(raw_files)} raw files found in {raw_dir}")
