import os
import glob
import logging
from datetime import datetime
from src.core.registry import get_parser, get_stage, STAGE_CANDIDATE_PARSING, STAGE_VALIDATION_NORMALIZATION
from src.core.storage.path_builder import HivePathBuilder
from src.core.storage.jsonl_writer import JsonlWriter
from src.core.utils.batch_util import BatchUtil

logger = logging.getLogger("process_project")

class ProcessService:
    @staticmethod
    def run_process(platform: str, category_cd: str) -> dict:
        """
        Process 프로젝트 비즈니스 로직.
        Raw 데이터 탐색 -> Stage2(파싱) -> Stage3(검증/정규화) 순으로 수행.
        """
        logger.info(f"--- Starting PROCESS Project: {platform}/{category_cd} ---")
        dt = datetime.now()
        
        # 1. 탐색 대상 Hive 경로 빌드 (Raw 수집 완료 데이터)
        base_path = HivePathBuilder.build_stage_base_path(
            process="raw", service="shop", category_cd=category_cd,
            stage="raw_collection", status="success", dt=dt
        )
        
        # 2. 배치 폴더 목록 확보
        batch_dirs = glob.glob(os.path.join(base_path, "batch_id=*"))
        if not batch_dirs:
            logger.info("No raw collection success data found for today.")
            return {"message": "No raw data found"}

        parser = get_parser(platform)
        stage2 = get_stage(STAGE_CANDIDATE_PARSING, parser=parser)
        stage3 = get_stage(STAGE_VALIDATION_NORMALIZATION)

        processed_batches = []
        for bdir in batch_dirs:
            batch_id = os.path.basename(bdir).split("=")[-1]
            logger.info(f"Processing Batch ID: {batch_id}")
            
            # 해당 배치의 JSONL 파일 합침
            raw_data = []
            for file in glob.glob(os.path.join(bdir, "*.jsonl")):
                raw_data.extend(JsonlWriter.read(file))
                
            if not raw_data:
                continue
            
            # 현재 배치 ID의 실제 run_attempt 조회
            run_attempt = BatchUtil.resolve_run_attempt(category_cd, batch_id, dt)
            filename = HivePathBuilder.build_filename(extension="jsonl", dt=dt)
            
            # --- 3. Stage 2: 후보 파싱 실행 ---
            candidates = stage2.execute(raw_data, batch_id, category_cd, run_attempt=run_attempt)
            
            s2_successes, s2_failures = [], []
            for r in candidates:
                if r.get("reason_code"):
                    # Design Policy: 실패 발생 즉시 retry_count 증가
                    r["retry_count"] = r.get("retry_count", 0) + 1
                    s2_failures.append(r)
                else:
                    s2_successes.append(r)
            
            # Stage 2 실패분 저장 (Stage 3 성공 여부와 무관하게 즉시 저장)
            if s2_failures:
                f2_path = HivePathBuilder.build_path(
                    process="normalized", service="shop", category_cd=category_cd,
                    stage="candidate_parsing", batch_id=batch_id, status="fail", dt=dt
                )
                JsonlWriter.write(f2_path, filename, s2_failures)
            
            # --- 4. Stage 3: 검증 및 정규화 실행 (Stage 2 성공분 대상으로) ---
            if s2_successes:
                normalized_results = stage3.execute(s2_successes, batch_id, category_cd, run_attempt=run_attempt)
                
                s3_successes, s3_failures = [], []
                for r in normalized_results:
                    if r.get("reason_code"):
                        # Design Policy: 실패 발생 즉시 retry_count 증가
                        r["retry_count"] = r.get("retry_count", 0) + 1
                        s3_failures.append(r)
                    else:
                        s3_successes.append(r)
                
                # Stage 3 결과 저장
                if s3_successes:
                    s3_succ_path = HivePathBuilder.build_path(
                        process="normalized", service="shop", category_cd=category_cd,
                        stage="validation_normalization", batch_id=batch_id, status="success", dt=dt
                    )
                    JsonlWriter.write(s3_succ_path, filename, s3_successes)
                    
                if s3_failures:
                    s3_fail_path = HivePathBuilder.build_path(
                        process="normalized", service="shop", category_cd=category_cd,
                        stage="validation_normalization", batch_id=batch_id, status="fail", dt=dt
                    )
                    JsonlWriter.write(s3_fail_path, filename, s3_failures)
                    
                processed_batches.append(batch_id)

        logger.info(f"--- PROCESS Project Finished ---")
        return {"processed_batches": processed_batches}
