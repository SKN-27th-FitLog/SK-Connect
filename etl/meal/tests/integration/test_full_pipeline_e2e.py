import os
import pytest
from unittest.mock import MagicMock
from datetime import date

# Import Stages
from src.pipeline.target_selection import TargetSelection
from src.pipeline.raw_collection import RawCollection
from src.pipeline.candidate_parsing import CandidateParsing
from src.pipeline.validation_normalization import ValidationNormalization
from src.pipeline.db_sync import DatabaseSync

# Import Handlers
from src.handlers.collect_raw_handler import CollectRawHandler
from src.handlers.parse_candidate_handler import ParseCandidateHandler
from src.handlers.validate_normalize_handler import ValidateNormalizeHandler
from src.handlers.db_sync_handler import DbSyncHandler

# Core/Storage
from src.storage.hive_path_builder import HivePathBuilder
from src.pipeline.dedup_service import DedupService
from src.repositories.store_repository import StoreRepository
from src.core.settings import settings

@pytest.fixture
def e2e_env(tmp_path):
    # 임시 테스트용 데이터 레이크 루트 
    test_root = str(tmp_path / "e2e_data_lake")
    pb = HivePathBuilder(base_root=test_root)
    
    # DB Mock
    db = MagicMock()
    # Stage 0용 리턴값 (1건)
    db.execute_query.side_effect = [
        [], # get_retry_targets
        [{"canonical_url": "https://restaurant.com/e2e"}] # get_new_candidates
    ]
    
    # Repo Mock
    repo = MagicMock(spec=StoreRepository)
    repo.save_store.return_value = 10101 # Final Shop ID
    
    # Dedup Mock
    dedup = MagicMock(spec=DedupService)
    dedup.get_dedup_info.return_value = {
        "is_duplicate": False, "type": None, "value": "key", "rule_version": "v1"
    }
    
    return {
        "path_builder": pb,
        "db": db,
        "repo": repo,
        "dedup": dedup,
        "root": test_root
    }

def test_full_pipeline_e2e_flow(e2e_env):
    pb = e2e_env["path_builder"]
    today = date.today()
    
    print("\n[E2E] Starting Full Pipeline Execution...")

    # --- [Stage 0] Target Selection ---
    selector = TargetSelection(db_client=e2e_env["db"], resolver=None, path_builder=pb)
    target_res = selector.run(category_cd="CA01", target_count=1)
    batch_id = target_res["batch_id"]
    
    meta_path = f"{pb.build('target_selection', 'success', dt=today)}/target_meta_{batch_id}.json"
    assert os.path.exists(meta_path), "Stage 0 meta file should exist."
    print(f"[E2E] Stage 0 OK: {meta_path}")

    # --- [Stage 1] Raw Collection ---
    mock_collector = MagicMock()
    mock_collector.collect.return_value = {
        "status": "success", "raw_content": "<h1 class='tit'>E2E Store</h1><p class='addr'>E2E Address</p>", "http_status": 200
    }
    
    raw_col_stage = RawCollection(collector=mock_collector, path_builder=pb)
    raw_handler = CollectRawHandler(raw_collector=raw_col_stage)
    raw_res = raw_handler.handle(meta_path)
    
    raw_file = raw_res["details"][0]["file_path"]
    assert os.path.exists(raw_file), "Stage 1 raw file should exist."
    print(f"[E2E] Stage 1 OK: {raw_file}")

    # --- [Stage 2] Candidate Parsing ---
    parsing_stage = CandidateParsing(path_builder=pb)
    parse_handler = ParseCandidateHandler(parser_stage=parsing_stage)
    parse_res = parse_handler.handle([raw_file])
    
    # cand_platform_a_id_123.jsonl (StoreParser mock values)
    cand_dir = pb.build("candidate", "success")
    jsonl_files = [f for f in os.listdir(cand_dir) if f.endswith(".jsonl")]
    assert len(jsonl_files) == 1, "Stage 2 candidate file should exist."
    cand_file = f"{cand_dir}/{jsonl_files[0]}"
    print(f"[E2E] Stage 2 OK: {cand_file}")

    # --- [Stage 3] Validation & Normalization ---
    val_norm_stage = ValidationNormalization(dedup_service=e2e_env["dedup"], path_builder=pb)
    val_handler = ValidateNormalizeHandler(val_norm_stage=val_norm_stage)
    val_res = val_handler.handle([cand_file])
    
    norm_dir = pb.build("normalized", "success")
    norm_files = [f for f in os.listdir(norm_dir) if f.endswith(".jsonl")]
    assert len(norm_files) == 1, "Stage 3 normalized file should exist."
    norm_file = f"{norm_dir}/{norm_files[0]}"
    print(f"[E2E] Stage 3 OK: {norm_file}")

    # --- [Stage 4] DB Sync ---
    db_sync_stage = DatabaseSync(repository=e2e_env["repo"])
    db_handler = DbSyncHandler(db_sync_stage=db_sync_stage)
    db_res = db_handler.handle([norm_file])
    
    # --- Final Assertion ---
    assert db_res["success_count"] == 1
    assert db_res["details"][0]["shop_id"] == 10101
    assert e2e_env["repo"].save_store.called, "DB Repository should have been called."
    
    print("\n[E2E] FULL PIPELINE SUCCESS: From Target Selection to DB Persistence!")
    print(f"Final Output: Shop ID {db_res['details'][0]['shop_id']}")
