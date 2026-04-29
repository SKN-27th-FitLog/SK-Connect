import os
import glob
from datetime import datetime
from src.core.storage.path_builder import HivePathBuilder
from src.core.storage.jsonl_writer import JsonlWriter

class BatchMetadataRepository:
    def find_batch_state_by_target_path(self, category_cd: str, selected_targets_path: str, dt: datetime) -> tuple:
        """대상 경로와 일치하는 기존 배치 ID 및 다음 실행 회차(run_attempt) 반환"""
        meta_base = HivePathBuilder.build_stage_base_path(
            process="metadata", service="shop", category_cd=category_cd,
            stage="batch_assignment", status="success", dt=dt
        )
        meta_files = glob.glob(os.path.join(meta_base, "batch_assignment_*.jsonl"))
        
        max_attempt, found_batch_id = 0, None
        for file in meta_files:
            for r in JsonlWriter.read(file):
                if r.get("selected_targets_path") == selected_targets_path:
                    found_batch_id = r.get("batch_id")
                    attempt = r.get("run_attempt", 1)
                    if attempt > max_attempt:
                        max_attempt = attempt
                        
        if found_batch_id:
            return found_batch_id, max_attempt + 1
        return None, 1
        
    def get_run_attempt(self, batch_id: str, category_cd: str, dt: datetime) -> int:
        """특정 배치 ID의 최신(최댓값) 실행 회차를 조회"""
        meta_base = HivePathBuilder.build_stage_base_path(
            process="metadata", service="shop", category_cd=category_cd,
            stage="batch_assignment", status="success", dt=dt
        )
        meta_files = glob.glob(os.path.join(meta_base, f"batch_assignment_{batch_id}_*.jsonl"))
        attempts = [1]
        for file in meta_files:
            for r in JsonlWriter.read(file):
                if r.get("batch_id") == batch_id:
                    attempts.append(r.get("run_attempt", 1))
        return max(attempts)
        
    def save_batch_metadata(self, batch_id: str, category_cd: str, selected_targets_path: str, run_attempt: int, dt: datetime):
        """배치 메타데이터(id, attempt 등)를 Hive 경로에 저장"""
        path = HivePathBuilder.build_path(
            process="metadata", service="shop", category_cd=category_cd,
            stage="batch_assignment", batch_id=batch_id, status="success", dt=dt
        )
        record = {
            "batch_id": batch_id,
            "category_cd": category_cd,
            "selected_targets_path": selected_targets_path,
            "run_attempt": run_attempt,
            "recorded_at": dt.isoformat()
        }
        JsonlWriter.write(
            path,
            HivePathBuilder.build_filename("jsonl", dt, stage="batch_assignment", batch_id=batch_id, run_attempt=run_attempt),
            [record],
        )
