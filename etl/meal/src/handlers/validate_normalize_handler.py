from typing import List, Dict, Any
from ..pipeline.validation_normalization import ValidationNormalization
from ..core.file_manager import logger

class ValidateNormalizeHandler:
    """
    Stage 3 실행 핸들러
    Candidate 파일들을 순회하며 검증, 정규화, 중복 제거를 조율합니다.
    """
    
    def __init__(self, val_norm_stage: ValidationNormalization):
        self.val_norm_stage = val_norm_stage

    def handle(self, candidate_file_paths: List[str]) -> Dict[str, Any]:
        """
        제공된 Candidate 파일 목록에 대해 처리를 실행합니다.
        """
        logger.info(f"========== [Handler] Starting Stage 3 for {len(candidate_file_paths)} files ==========")
        
        success_count = 0
        duplicate_count = 0
        fail_count = 0
        results = []

        for path in candidate_file_paths:
            res = self.val_norm_stage.run(path)
            
            if res["status"] == "success":
                success_count += 1
            elif res["status"] == "duplicate":
                duplicate_count += 1
            else:
                fail_count += 1
                
            results.append({
                "source_path": path,
                "status": res["status"],
                "reason_code": res.get("reason_code")
            })

        logger.info(f"========== [Handler] Stage 3 Finished: Success={success_count}, Dupe={duplicate_count}, Fail={fail_count} ==========")
        
        return {
            "total_count": len(candidate_file_paths),
            "success_count": success_count,
            "duplicate_count": duplicate_count,
            "fail_count": fail_count,
            "details": results
        }
