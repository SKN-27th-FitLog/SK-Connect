from typing import List, Dict, Any
from ..pipeline.db_sync import DatabaseSync
from ..core.file_manager import logger

class DbSyncHandler:
    """
    Stage 4 실행 핸들러
    정규화된 파일들을 순회하며 DB에 적재하고 최종 결과를 보고합니다.
    """
    
    def __init__(self, db_sync_stage: DatabaseSync):
        self.db_sync_stage = db_sync_stage

    def handle(self, normalized_file_paths: List[str]) -> Dict[str, Any]:
        """
        제공된 Normalized 파일 목록에 대해 DB 적재를 실행합니다.
        """
        logger.info(f"========== [Handler] Starting Stage 4 for {len(normalized_file_paths)} files ==========")
        
        success_count = 0
        fail_count = 0
        results = []

        for path in normalized_file_paths:
            res = self.db_sync_stage.run(path)
            
            if res["status"] == "success":
                success_count += 1
            else:
                fail_count += 1
                
            results.append({
                "source_path": path,
                "status": res["status"],
                "shop_id": res.get("shop_id"),
                "reason_code": res.get("reason_code")
            })

        logger.info(f"========== [Handler] Stage 4 Finished: Success={success_count}, Fail={fail_count} ==========")
        
        return {
            "total_count": len(normalized_file_paths),
            "success_count": success_count,
            "fail_count": fail_count,
            "details": results
        }
