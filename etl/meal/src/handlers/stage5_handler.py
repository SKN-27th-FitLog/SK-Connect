from src.pipeline.stages.stage5_fail_classification import Stage5FailClassification

def handler(event, context):
    """
    Stage 5: Fail Classification 전용 핸들러.
    Input: { "all_failures": [...], "batch_id": "...", "category_cd": "..." }
    """
    all_failures = event.get("all_failures", [])
    batch_id = event.get("batch_id")
    category_cd = event.get("category_cd")

    if not all_failures:
        return {"statusCode": 200, "message": "No failures to classify."}

    stage = Stage5FailClassification()
    results = stage.execute(all_failures, batch_id, category_cd)
    
    return {
        "statusCode": 200,
        "classified_failures": results
    }
