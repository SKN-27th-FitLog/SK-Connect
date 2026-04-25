import os
import glob
import logging
from datetime import datetime
from src.core.storage.path_builder import HivePathBuilder
from src.core.storage.jsonl_writer import JsonlWriter
from src.core.resolver import Resolver
from src.core.dispatch import Dispatcher

logger = logging.getLogger("failcheck_project")

class FailcheckService:
    @staticmethod
    def run_failcheck(category_cd: str) -> dict:
        """
        Failcheck 프로젝트 비즈니스 로직.
        오늘 발생한 모든 실패 파일을 수집 -> Resolver(판단) -> Dispatcher(라우팅) 수행.
        """
        logger.info(f"--- Starting FAILCHECK Project: {category_cd} ---")
        dt = datetime.now()
        date_str = dt.strftime('%Y%n%d') # Design Policy: 동일 날짜 반복 재시도 방지용 스트링
        
        # 1. 모든 스테이지의 실패(status=fail) 파일 수집
        fail_files = []
        for stage_name in ["raw_collection", "candidate_parsing", "validation_normalization", "load"]:
            # 각 스테이지의 적절한 process_type 결정
            process_type = "raw" if stage_name == "raw_collection" else \
                          ("load" if stage_name == "load" else "normalized")
            
            base_fail_path = HivePathBuilder.build_stage_base_path(
                process=process_type, service="shop", category_cd=category_cd,
                stage=stage_name, status="fail", dt=dt
            )
            fail_files.extend(glob.glob(os.path.join(base_fail_path, "batch_id=*", "*.jsonl")))

        if not fail_files:
            logger.info("No failed records found for today.")
            return {"message": "No failed records found"}

        # 2. 모든 레코드 로드
        failed_records = []
        for file in fail_files:
            failed_records.extend(JsonlWriter.read(file))

        logger.info(f"Gathered {len(failed_records)} failed records. Deciding follow-up actions.")

        # 3. 레코드별 후속 행동 결정 및 분파(Dispatch)
        for record in failed_records:
            # Policy 1: 재시도 횟수 제한 및 동일 날짜 중복 처리 방지
            retry_count = record.get("retry_count", 0)
            last_retry_date = record.get("last_retry_date")

            # 오늘 이미 재시도했거나, 재시도 횟수가 5회를 넘겼으면 DROP
            if last_retry_date == date_str:
                logger.info(f"Skipping record {record.get('target_id')} - Already retried today.")
                continue
                
            if retry_count >= 5:
                logger.warning(f"Retry limit (5) exceeded for {record.get('target_id')}. Dropping.")
                action = "DROP"
            else:
                # Policy 2: Resolver에 판단 위임
                reason_code = record.get("reason_code")
                action = Resolver.decide_action(reason_code, record)
            
            # 메타데이터 업데이트 (재시도 날짜 기록 또는 폐기 기록)
            if action in ("RETRY_CRAWL", "REPROCESS", "RETRY_SAVE"):
                record["last_retry_date"] = date_str
            elif action == "DROP":
                record["final_action"] = "DROP"
                record["dropped_at"] = dt.isoformat()
            
            # Policy 3: Dispatcher에 라우팅 위임 (물리적 파일 저장)
            Dispatcher.dispatch(action, record, dt)

        # 고유 배치 ID 목록 추출 (로깅용)
        processed_batches = list(set([r.get("batch_id") for r in failed_records if r.get("batch_id")]))
        
        logger.info(f"--- FAILCHECK Project Finished ---")
        return {
            "processed_batches": processed_batches,
            "records_processed": len(failed_records)
        }
