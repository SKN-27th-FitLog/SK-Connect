from src.pipeline.stages.stage2_candidate_parsing import Stage2CandidateParsing
from src.services.parsers.diningcode_parser import DiningCodeParser
from src.core.storage.jsonl_writer import JsonlWriter

def handler(event, context):
    """
    Stage 2 Handler (Path-based).
    Input: { "raw_metadata_path": "...", "batch_id": "...", "category_cd": "..." }
    """
    path = event.get("raw_metadata_path")
    batch_id = event.get("batch_id")
    category_cd = event.get("category_cd")

    # 1. 파일에서 데이터 로드 (메모리 절약)
    raw_metadata = JsonlWriter.read(path)
    
    parser = DiningCodeParser()
    stage = Stage2CandidateParsing(parser)
    results = stage.execute(raw_metadata, batch_id, category_cd)
    
    # 2. 결과물은 Stage 내부에서 이미 파일로 저장되었으므로, 해당 경로를 추적하여 반환
    # (Stage 2 execute 내부에서 JsonlWriter를 호출할 때 사용한 경로를 반환하도록 수정 필요하거나
    #  여기서 명시적으로 경로를 구성)
    
    from src.core.storage.path_builder import HivePathBuilder
    from datetime import datetime
    
    # 마지막 파일 경로 구성 (실제로는 execute에서 반환하도록 리팩토링하는 것이 좋음)
    result_path = HivePathBuilder.build_path(
        process="candidate", service="shop", category_cd=category_cd,
        stage="candidate_parsing", batch_id=batch_id, status="success"
    )
    # 가장 최근 파일 찾기 로직 등 추가 가능
    
    return {
        "statusCode": 200,
        "next_payload": {
            "candidates_path": result_path, # 데이터 대신 경로 전달
            "batch_id": batch_id,
            "category_cd": category_cd
        }
    }
