import os
import json
import pytest
from src.pipeline.candidate_parsing import CandidateParsing
from src.handlers.parse_candidate_handler import ParseCandidateHandler
from src.storage.hive_path_builder import HivePathBuilder
from src.models.store_models import StoreCandidate

def test_stage1_to_stage2_integration(tmp_path):
    # 1. 초기 설정 (임시 경로 사용)
    data_lake_root = str(tmp_path / "data_lake")
    path_builder = HivePathBuilder(base_root=data_lake_root)
    
    # 2. 가상의 Raw 파일 생성 (Stage 1 결과물 모사)
    raw_dir = path_builder.build(stage="raw", status="success")
    os.makedirs(raw_dir, exist_ok=True)
    
    raw_file_path = f"{raw_dir}/test_store.html"
    html_content = """
    <html>
        <body>
            <h1 class="tit">맛있는 파스타집</h1>
            <p class="addr">서울시 강남구 역삼동 123-45</p>
        </body>
    </html>
    """
    with open(raw_file_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    # 3. Handler를 통해 Stage 2 실행
    parser_stage = CandidateParsing(path_builder=path_builder)
    handler = ParseCandidateHandler(parser_stage=parser_stage)
    
    handler_res = handler.handle(raw_file_paths=[raw_file_path])
    
    # 4. 검증
    assert handler_res["success_count"] == 1
    
    # 생성된 JSONL 파일 확인
    cand_dir = path_builder.build(stage="candidate", status="success")
    jsonl_files = [f for f in os.listdir(cand_dir) if f.endswith(".jsonl")]
    
    assert len(jsonl_files) == 1
    
    # 파일 내용 스키마 검증
    jsonl_path = f"{cand_dir}/{jsonl_files[0]}"
    with open(jsonl_path, "r", encoding="utf-8") as f:
        line = f.readline()
        data = json.loads(line)
        
        # Pydantic 모델로 다시 로드하여 검증
        candidate = StoreCandidate(**data)
        assert candidate.name == "맛있는 파스타집"
        assert "서울시 강남구" in candidate.address
        
    print(f"\n--- Stage 1-2 Integration Success: Candidate saved to {jsonl_path}")
