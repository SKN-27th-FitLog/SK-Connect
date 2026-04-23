import json
from typing import List, Dict, Any
from ..pipeline.raw_collection import RawCollection
from ..core.file_manager import logger

class CollectRawHandler:
    """
    Stage 1 실행 핸들러
    Stage 0에서 생성된 Target Meta JSON 파일을 읽어 대량 수집을 수행합니다.
    """
    
    def __init__(self, raw_collector: RawCollection = None):
        self.raw_collector = raw_collector or RawCollection()

    def handle(self, meta_file_path: str) -> Dict[str, Any]:
        """
        메타데이터 파일을 읽어 모든 타겟에 대해 수집을 실행합니다.
        """
        logger.info(f"========== [Handler] Starting Stage 1 for meta: {meta_file_path} ==========")
        
        # 1. 메타데이터 로드
        try:
            with open(meta_file_path, "r", encoding="utf-8") as f:
                meta_data = json.load(f)
        except Exception as e:
            logger.error(f"!!! [Handler] Failed to read meta file: {e}")
            return {"status": "fail", "reason": "META_READ_ERROR"}

        candidate_urls = meta_data.get("candidate_store_ids", [])
        batch_id = meta_data.get("batch_id")
        category_cd = meta_data.get("category_cd")
        
        logger.info(f"--- [Handler] Batch: {batch_id}, Found {len(candidate_urls)} URLs.")

        success_count = 0
        fail_count = 0
        results = []

        # 2. 각 URL별로 Stage 1(RawCollection) 실행
        for url in candidate_urls:
            res = self.raw_collector.run(url)
            
            if res.status == "success":
                success_count += 1
            else:
                fail_count += 1
                
            results.append({
                "url": url,
                "status": res.status,
                "file_path": res.file_path,
                "reason_code": res.reason_code
            })

        logger.info(f"========== [Handler] Stage 1 Finished: Success={success_count}, Fail={fail_count} ==========")
        
        return {
            "batch_id": batch_id,
            "category_cd": category_cd,
            "total_count": len(candidate_urls),
            "success_count": success_count,
            "fail_count": fail_count,
            "details": results
        }
