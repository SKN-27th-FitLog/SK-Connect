import asyncio
import logging
from src.pipeline.stages.stage1_raw_collection import Stage1RawCollection
from src.core.registry import get_collector

logger = logging.getLogger(__name__)

def handler(event, context):
    """
    Stage 1 Handler (Registry optimized).
    """
    targets = event.get("targets", [])
    batch_id = event.get("batch_id")
    category_cd = event.get("category_cd")
    platform = event.get("platform", "DiningCode")

    # 레지스트리에서 플랫폼 이름만으로 수집기 획득
    collector = get_collector(platform)
    stage = Stage1RawCollection(collector)
    
    loop = asyncio.get_event_loop()
    results = loop.run_until_complete(stage.execute(targets, batch_id, category_cd))
    
    return {
        "statusCode": 200,
        "next_payload": {
            "raw_metadata": results,
            "batch_id": batch_id,
            "category_cd": category_cd,
            "platform": platform
        }
    }
