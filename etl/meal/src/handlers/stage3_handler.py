from src.pipeline.stages.stage3_validation_normalization import Stage3ValidationNormalization

def handler(event, context):
    """
    Stage 3: Validation & Normalization 전용 핸들러.
    Input: { "candidates": [...], "batch_id": "...", "category_cd": "..." }
    """
    candidates = event.get("candidates", [])
    batch_id = event.get("batch_id")
    category_cd = event.get("category_cd")

    stage = Stage3ValidationNormalization()
    results = stage.execute(candidates, batch_id, category_cd)
    
    return {
        "statusCode": 200,
        "next_payload": {
            "normalized_data": results,
            "batch_id": batch_id,
            "category_cd": category_cd
        }
    }
