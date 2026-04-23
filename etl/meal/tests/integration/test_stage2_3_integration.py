import os
import json
import pytest
from unittest.mock import MagicMock
from src.pipeline.validation_normalization import ValidationNormalization
from src.handlers.validate_normalize_handler import ValidateNormalizeHandler
from src.pipeline.dedup_service import DedupService
from src.core.storage.hive_path_builder import HivePathBuilder
from src.db.models.store_models import NormalizedStore

@pytest.fixture
def mock_dedup():
    service = MagicMock(spec=DedupService)
    # 기본적으로 중복 아님을 반환
    service.get_dedup_info.return_value = {
        "is_duplicate": False,
        "type": None,
        "value": "normalized_name|normalized_address",
        "rule_version": "v1.0"
    }
    return service

def test_stage2_to_stage3_integration(mock_dedup, tmp_path):
    # 1. 초기 설정
    data_lake_root = str(tmp_path / "data_lake")
    path_builder = HivePathBuilder(base_root=data_lake_root)
    
    # 2. 가상의 Candidate 파일 생성 (특수문자와 공백이 섞인 상호명)
    cand_dir = path_builder.build(stage="candidate", status="success")
    os.makedirs(cand_dir, exist_ok=True)
    
    cand_file_path = f"{cand_dir}/cand_test_001.jsonl"
    cand_data = {
        "source_platform": "naver",
        "source_internal_id": "12345",
        "name": "맛있는 (파스타) 집!!! ",
        "address": " 서울시 강남구  역삼동 123 ",
        "canonical_url": "https://restaurant.com/1",
        "category_cd": "CA01",
        "extracted_at": "2026-04-23T12:00:00"
    }
    with open(cand_file_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(cand_data) + "\n")

    # 3. Handler를 통해 Stage 3 실행
    val_norm_stage = ValidationNormalization(dedup_service=mock_dedup, path_builder=path_builder)
    handler = ValidateNormalizeHandler(val_norm_stage=val_norm_stage)
    
    handler_res = handler.handle(candidate_file_paths=[cand_file_path])
    
    # 4. 검증
    assert handler_res["success_count"] == 1
    
    # 생성된 Normalized 파일 확인
    norm_dir = path_builder.build(stage="normalized", status="success")
    norm_files = [f for f in os.listdir(norm_dir) if f.endswith(".jsonl")]
    
    assert len(norm_files) == 1
    
    # 정규화 내용 검증
    norm_path = f"{norm_dir}/{norm_files[0]}"
    with open(norm_path, "r", encoding="utf-8") as f:
        data = json.loads(f.readline())
        
        # 정규화된 상호명: 특수문자 제거, 공백 하나로 축소, 소문자화
        assert data["normalized_name"] == "맛있는 파스타 집"
        # 정규화된 주소: 연속 공백 축소
        assert data["normalized_address"] == "서울시 강남구 역삼동 123"
        
    print(f"\n--- Stage 2-3 Integration Success: Normalized data saved to {norm_path}")
