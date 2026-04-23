import os
import sys
import json
from datetime import date
from unittest.mock import MagicMock

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 모듈 임포트
from src.core.settings import settings
from src.storage.hive_path_builder import HivePathBuilder
from src.pipeline.target_selection import TargetSelection
from src.pipeline.raw_collection import RawCollection
from src.pipeline.candidate_parsing import CandidateParsing
from src.pipeline.validation_normalization import ValidationNormalization
from src.pipeline.db_sync import DatabaseSync
from src.pipeline.dedup_service import DedupService
from src.repositories.store_repository import StoreRepository

def run_real_demo():
    print("[Step 0] 데모 파이프라인 시작...")
    
    # 설정 초기화
    demo_root = os.path.join(os.getcwd(), "demo_data_lake")
    pb = HivePathBuilder(base_root=demo_root)
    
    # 1. 대상 URL 설정
    target_url = "https://m.place.naver.com/restaurant/demo_12345/home"
    print(f"URL: {target_url}\n")

    # --- [Stage 0] Target Selection ---
    # DB에서 해당 URL을 뽑아왔다고 가정
    db = MagicMock()
    db.execute_query.side_effect = [[], [{"canonical_url": target_url}]]
    selector = TargetSelection(db_client=db, resolver=None, path_builder=pb)
    target_res = selector.run(category_cd="CA01", target_count=1)
    
    meta_path = f"{pb.build('target_selection', 'success', dt=date.today())}/target_meta_{target_res['batch_id']}.json"
    print(f"[Stage 0 Done] Meta Path:\n   -> {meta_path}\n")

    # --- [Stage 1] Raw Collection ---
    # 실제 수집을 시뮬레이션하기 위한 Mock HTML
    mock_html = f"<html><body><h1 class='tit'>데모 맛집</h1><p class='addr'>서울시 강남구 삼성동 100</p><div id='id'>demo_id_999</div></body></html>"
    mock_collector = MagicMock()
    mock_collector.collect.return_value = {"status": "success", "raw_content": mock_html, "http_status": 200}
    
    raw_col = RawCollection(collector=mock_collector, path_builder=pb)
    # TargetSelection의 결과(meta_path)를 읽어 처리하는 과정을 핸들러 없이 직접 수행
    raw_res = raw_col.run(target_url)
    print(f"[Stage 1 Done] Raw Path:\n   -> {raw_res.file_path}\n")

    # --- [Stage 2] Candidate Parsing ---
    parsing_stage = CandidateParsing(path_builder=pb)
    parse_res = parsing_stage.run(raw_res.file_path) # BaseStage.run(input) 호출
    
    # 실제 저장된 파일 찾기
    cand_dir = pb.build("candidate", "success")
    cand_file = f"{cand_dir}/{os.listdir(cand_dir)[0]}"
    print(f"[Stage 2 Done] Candidate Path:\n   -> {cand_file}\n")

    # --- [Stage 3] Validation & Normalization ---
    dedup = MagicMock(spec=DedupService)
    dedup.get_dedup_info.return_value = {"is_duplicate": False, "type": None, "value": "demo_key", "rule_version": "v4"}
    
    val_norm = ValidationNormalization(dedup_service=dedup, path_builder=pb)
    val_res = val_norm.run(cand_file)
    
    norm_dir = pb.build("normalized", "success")
    norm_file = f"{norm_dir}/{os.listdir(norm_dir)[0]}"
    print(f"[Stage 3 Done] Normalized Path:\n   -> {norm_file}\n")

    # --- [Stage 4] DB Sync (최종 관문) ---
    repo = MagicMock(spec=StoreRepository)
    repo.save_store.return_value = 8888 
    
    db_sync = DatabaseSync(repository=repo)
    db_res = db_sync.run(norm_file)
    
    print("[Stage 4 Done] DB Sync Success!")
    print(f"   Final ID: {db_res['shop_id']}")
    
    # 최종적으로 DB에 전달된 데이터 내용 확인
    inserted_data = repo.save_store.call_args[0][0]
    print("\n[Final DB Data Check]")
    print(json.dumps(inserted_data, indent=4, ensure_ascii=False))
    
    print("\nDemo finished successfully.")

if __name__ == "__main__":
    run_real_demo()
