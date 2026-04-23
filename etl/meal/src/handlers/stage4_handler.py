from src.pipeline.stages.stage4_load import Stage4Load

def handler(event, context):
    """
    Stage 4: Load 전용 핸들러.
    Input: { "normalized_data": [...], "batch_id": "...", "category_cd": "..." }
    """
    normalized_data = event.get("normalized_data", [])
    batch_id = event.get("batch_id")
    category_cd = event.get("category_cd")

    stage = Stage4Load()
    results = stage.execute(normalized_data, batch_id, category_cd)
    
    # 실패 리스트 추출 (Stage 5 전달용)
    failures = [r for r in results if r["status"] == "fail"]

    return {
        "statusCode": 200,
        "load_results": results,
        "next_payload": {
            "all_failures": failures,
            "batch_id": batch_id,
            "category_cd": category_cd
        }
    }
