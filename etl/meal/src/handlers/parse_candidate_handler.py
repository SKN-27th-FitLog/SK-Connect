from typing import List, Dict, Any
from ..pipeline.candidate_parsing import CandidateParsing
from ..core.file_manager import logger

class ParseCandidateHandler:
    """
    Stage 2 실행 핸들러
    Stage 1에서 생성된 Raw 파일들을 순회하며 파싱을 수행합니다.
    """
    
    def __init__(self, parser_stage: CandidateParsing = None):
        self.parser_stage = parser_stage or CandidateParsing()

    def handle(self, raw_file_paths: List[str]) -> Dict[str, Any]:
        """
        제공된 Raw 파일 목록에 대해 파싱을 실행합니다.
        """
        logger.info(f"========== [Handler] Starting Stage 2 for {len(raw_file_paths)} files ==========")
        
        success_count = 0
        fail_count = 0
        results = []

        for path in raw_file_paths:
            res = self.parser_stage.run(path)
            
            if res["status"] == "success":
                success_count += 1
            else:
                fail_count += 1
                
            results.append({
                "source_path": path,
                "status": res["status"],
                "reason_code": res.get("reason_code")
            })

        logger.info(f"========== [Handler] Stage 2 Finished: Success={success_count}, Fail={fail_count} ==========")
        
        return {
            "total_count": len(raw_file_paths),
            "success_count": success_count,
            "fail_count": fail_count,
            "details": results
        }
