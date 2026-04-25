import logging
import os
from datetime import datetime
from src.core.config import settings
from src.core.storage.path_builder import HivePathBuilder
from src.core.storage.jsonl_writer import JsonlWriter

class Dispatcher:
    @staticmethod
    def dispatch(action: str, record: dict, dt: datetime):
        """
        resolver에 의해 결정된 action에 따라 레코드를 적절한 Hive 경로로 분기 및 저장.
        """
        category_cd = record.get("category_cd")
        batch_id = record.get("batch_id")
        
        # Design Policy: 필수 메타데이터 누락 시 Hive 구조 파괴 방지를 위해 metadata_error 경로로 격리
        if not category_cd or not batch_id:
            record["missing_metadata"] = {
                "category_cd_missing": not category_cd,
                "batch_id_missing": not batch_id
            }
            record["final_action"] = "MANUAL_CHECK"
            record["dropped_at"] = dt.isoformat()
            
            # 카테고리 계층을 통째로 우회하는 전용 격리 경로
            isolated_path = os.path.join(
                settings.LAKE_ROOT_PATH, 
                "process=dropped", "service=metadata_error", 
                "status=manual_check", "stage=invalid_fail_record"
            )
            JsonlWriter.write(isolated_path, HivePathBuilder.build_filename("jsonl", dt), [record])
            return
        
        # 재시도/재처리의 경우 출처 추적 정보 추가
        if action in ("RETRY_CRAWL", "REPROCESS", "RETRY_SAVE"):
            record["origin_batch_id"] = record.get("batch_id")
            record["batch_type"] = "REPROCESS" if action == "REPROCESS" else "RETRY"
            
        # Action별 경로 매핑
        if action == "RETRY_CRAWL":
            process, stage = "retry", "raw_collection"
        elif action == "REPROCESS":
            process, stage = "retry", "candidate_parsing"
        elif action == "RETRY_SAVE":
            process, stage = "retry", "load"
        elif action == "DROP":
            process, stage = "dropped", "final_drop"
        elif action == "MANUAL_CHECK":
            process, stage = "dropped", "manual_check"
        else:
            # 알 수 없는 결정은 수동 확인으로 분류
            process, stage = "dropped", "manual_check"
            record["final_action"] = "MANUAL_CHECK"
            record["dropped_at"] = dt.isoformat()
            
        path = HivePathBuilder.build_path(
            process=process, service="shop", category_cd=category_cd,
            stage=stage, batch_id=batch_id, status=action.lower(), dt=dt
        )
        
        filename = HivePathBuilder.build_filename(extension="jsonl", dt=dt)
        JsonlWriter.write(path, filename, [record])
