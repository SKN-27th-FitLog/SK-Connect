from datetime import datetime, timedelta
from src.core.config import settings
from src.core.storage.path_builder import HivePathBuilder
from src.core.storage.jsonl_writer import JsonlWriter

class Dispatcher:
    @staticmethod
    def dispatch(action: str, record: dict, dt: datetime):
        """
        사용자 요구사항 준수 - 결정된 action에 따라 고정된 규격의 파일로 저장.
        """
        category_cd = record.get("category_cd", "UNKNOWN")
        batch_id = record.get("batch_id", "UNKNOWN")
        
        # 1. Action별 산출물 규격 및 날짜 파티션 결정
        if action == "RETRY":
            # Action.RETRY인 경우 다음날 partition의 retry_items.jsonl에 기록 (동일 날짜 재시도 금지)
            target_dt = dt + timedelta(days=1)
            filename = "retry_items.jsonl"
            process, status = "retry", "pending"
        elif action == "REPROCESS":
            # Action.REPROCESS인 경우 reprocess_items.jsonl에 기록 
            # (파서/정규화 룰 수정, 코드 테이블 보강, 운영 검토 후 재처리 대상 기록)
            target_dt = dt
            filename = "reprocess_items.jsonl"
            process, status = "reprocess", "pending"
        elif action in ("DROP", "MANUAL_CHECK"):
            # Action.DROP인 경우 drop_items.jsonl에 기록
            target_dt = dt
            filename = "drop_items.jsonl"
            process, status = "dropped", "final_drop"
        else:
            # 기타 경고 및 예외 케이스
            target_dt = dt
            filename = "warning_summary.jsonl"
            process, status = "warning", "check"

        # 2. Hive 스타일 경로 생성
        path = HivePathBuilder.build_path(
            process=process, service="shop", category_cd=category_cd,
            stage="fail_handling", batch_id=batch_id, status=status, dt=target_dt
        )
        
        # 3. 파일 기록 (배치 내 레코드를 append 또는 신규 생성)
        JsonlWriter.write(path, filename, [record])
