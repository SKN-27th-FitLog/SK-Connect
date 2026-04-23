import os
import sys
import json
from unittest.mock import MagicMock

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.storage.hive_path_builder import HivePathBuilder
from src.pipeline.validation_normalization import ValidationNormalization
from src.pipeline.db_sync import DatabaseSync
from src.pipeline.dedup_service import DedupService
from src.db.repositories.store_repository import StoreRepository

def run_manual_finish():
    # 1. Candidate 폴더에서 최신 파일 찾기
    pb = HivePathBuilder(base_root="diningcode_real_lake")
    cand_dir = pb.build("candidate", "success")
    
    if not os.path.exists(cand_dir) or not os.listdir(cand_dir):
        print(f"!!! Candidate 파일을 찾을 수 없습니다: {cand_dir}")
        return
        
    # 가장 최근에 생성된 .jsonl 파일 선택
    jsonl_files = [f for f in os.listdir(cand_dir) if f.endswith(".jsonl")]
    jsonl_files.sort(key=lambda x: os.path.getmtime(os.path.join(cand_dir, x)), reverse=True)
    cand_file = os.path.join(cand_dir, jsonl_files[0])
    print(f"-> 처리할 파일 선정: {cand_file}")

    # 2. 초기화 (설정 및 Mock 객체)
    pb = HivePathBuilder(base_root="diningcode_real_lake")
    
    # 중복 체크 Mock (무조건 신규 데이터로 가정)
    dedup = MagicMock(spec=DedupService)
    dedup.get_dedup_info.return_value = {
        "is_duplicate": False, 
        "type": None, 
        "value": "demo_key_morisushi", 
        "rule_version": "v4"
    }
    
    # DB 저장 Mock
    repo = MagicMock(spec=StoreRepository)
    repo.save_store.return_value = 7777 # 수동 실행 성공 ID
    
    # 3. Stage 3 (정규화 및 검증) 실행
    print("\n[Step 3] 데이터 정규화 및 중복 체크 중...")
    val_norm = ValidationNormalization(dedup_service=dedup, path_builder=pb)
    val_res = val_norm.run(cand_file)
    
    # 생성된 Normalized 파일 경로 확보
    norm_dir = pb.build("normalized", "success")
    norm_file = os.path.join(norm_dir, os.listdir(norm_dir)[0])
    print(f"-> 정규화 완료! 파일 저장 위치: {norm_file}")

    # 4. Stage 4 (DB 적재) 실행
    print("\n[Step 4] 데이터베이스 적재(Mock) 중...")
    db_sync = DatabaseSync(repository=repo)
    db_res = db_sync.run(norm_file)
    print(f"-> DB 적재 시도 성공! (새로운 Shop ID: {db_res['shop_id']})")

    # 5. 최종 데이터 내용 확인
    inserted_data = repo.save_store.call_args[0][0]
    print("\n[최종 DB 적재 데이터 내역]")
    print(json.dumps(inserted_data, indent=4, ensure_ascii=False))
    print("\n수고하셨습니다! 전 공정이 완료되었습니다.")

if __name__ == "__main__":
    run_manual_finish()
