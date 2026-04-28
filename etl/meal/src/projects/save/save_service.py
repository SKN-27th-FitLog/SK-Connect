import os
import glob
import logging
from datetime import datetime
from src.core.registry import get_stage, get_repository, STAGE_LOAD
from src.core.storage.path_builder import HivePathBuilder
from src.core.storage.jsonl_writer import JsonlWriter
from src.core.utils.batch_util import BatchUtil
from src.core.policy.fail_record import build_fail_record
from src.core.policy.reason_code import ReasonCode

logger = logging.getLogger("save_project")

class SaveService:
    @staticmethod
    def run_save(category_cd: str) -> dict:
        """
        Save 프로젝트 비즈니스 로직.
        정규화 데이터 탐색 -> 참조 무결성 재검증 -> Stage4(DB 적재) 순으로 수행.
        """
        logger.info(f"--- Starting SAVE Project: {category_cd} ---")
        dt = datetime.now()
        
        # 1. 탐색 대상 Hive 경로 빌드 (정규화 완료 데이터)
        base_path = HivePathBuilder.build_stage_base_path(
            process="normalized", service="shop", category_cd=category_cd,
            stage="validation_normalization", status="success", dt=dt
        )
        
        # 2. 배치 폴더 목록 확보
        batch_dirs = glob.glob(os.path.join(base_path, "batch_id=*", "status=success"))
        if not batch_dirs:
            logger.info("No normalization success data found for today.")
            return {"message": "No normalized data found"}

        stage4 = get_stage(STAGE_LOAD)
        code_repo = get_repository("code_table")
        
        processed_batches = []
        for bdir in batch_dirs:
            batch_id = os.path.basename(os.path.dirname(bdir)).split("=")[-1]
            logger.info(f"Processing Batch ID: {batch_id}")
            
            # 정규화된 JSONL 데이터 로드
            normalized_data = []
            for file in glob.glob(os.path.join(bdir, "*.jsonl")):
                normalized_data.extend(JsonlWriter.read(file))
                
            if not normalized_data:
                continue
            
            run_attempt = BatchUtil.resolve_run_attempt(category_cd, batch_id, dt)
            filename = HivePathBuilder.build_filename(extension="jsonl", dt=dt)
            
            # --- 3. 참조 무결성 재검증 (Load 전 필수 단계) ---
            valid_list, failures = [], []
            for r in normalized_data:
                if not code_repo.validate_references(r):
                    # Design Policy: 참조 오류 시 즉시 retry_count 증가 및 실패 처리
                    store = r.get("store", {})
                    failures.append(build_fail_record(
                        batch_id=batch_id,
                        run_attempt=run_attempt,
                        stage="load",
                        entity_type="store",
                        entity_id=store.get("entity_id", r.get("entity_id", "unknown")),
                        entity_ref=store.get("entity_ref", r.get("entity_ref", {})),
                        reason_code=ReasonCode.REFERENCE_INTEGRITY_VIOLATION,
                        retry_count=r.get("retry_count", 0) + 1,
                        detail="Reference integrity validation failed before load.",
                        data=r,
                    ))
                else:
                    valid_list.append(r)

            # --- 4. Stage 4: DB 적재 실행 ---
            load_successes = []
            if valid_list:
                load_results = stage4.execute(valid_list, batch_id, category_cd, run_attempt=run_attempt)
                for r in load_results:
                    if r.get("reason_code"):
                        # Design Policy: 적재 실패 시 즉시 retry_count 증가
                        r["retry_count"] = r.get("retry_count", 0) + 1
                        failures.append(r)
                    else:
                        load_successes.append(r)

            # --- 5. 결과 저장 및 물리적 분리 ---
            if load_successes:
                succ_path = HivePathBuilder.build_path(
                    process="load", service="shop", category_cd=category_cd,
                    stage="load", batch_id=batch_id, status="success", dt=dt
                )
                filename_succ = f"{dt.strftime('%y%m%d%H%M%S')}_att{run_attempt}.jsonl"
                JsonlWriter.write(succ_path, filename_succ, load_successes)
                
            if failures:
                fail_path = HivePathBuilder.build_path(
                    process="load", service="shop", category_cd=category_cd,
                    stage="load", batch_id=batch_id, status="fail", dt=dt
                )
                filename_fail = f"{dt.strftime('%y%m%d%H%M%S')}_att{run_attempt}_fail.jsonl"
                JsonlWriter.write(fail_path, filename_fail, failures)
            
            processed_batches.append(batch_id)
                
        logger.info(f"--- SAVE Project Finished ---")
        return {"processed_batches": processed_batches}
