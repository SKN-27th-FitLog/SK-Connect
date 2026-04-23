import os
import sys
import json
from datetime import date
from unittest.mock import MagicMock

# 프로젝트 루트를 sys.path에 추가 (scripts/ 하위에서 실행 시 필요)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 모듈 임포트
from src.core.settings import settings
from src.storage.hive_path_builder import HivePathBuilder
from src.pipeline.target_selection import TargetSelection
from src.pipeline.raw_collection import RawCollection
from src.pipeline.candidate_parsing import CandidateParsing
from src.pipeline.validation_normalization import ValidationNormalization
from src.pipeline.db_sync import DatabaseSync
from src.pipeline.fail_classification import FailClassification
from src.collectors.http_collector import HttpCollector
from src.pipeline.dedup_service import DedupService
from src.repositories.store_repository import StoreRepository

def run_diningcode_demo():
    print("[Real URL Demo] 다이닝코드 수집 테스트 시작...")
    
    # 1. 초기화
    demo_root = os.path.join(os.getcwd(), "diningcode_real_lake")
    pb = HivePathBuilder(base_root=demo_root)
    target_url = "https://www.diningcode.com/profile.php?rid=BNTwJFsOjGL9" # 모리스시 상세페이지
    
    # --- [Stage 1] Real Raw Collection ---
    print(f"\n[Stage 1] 실제 네트워크 수집 시도: {target_url}")
    # 가짜가 아닌 진짜 HttpCollector 사용
    collector = HttpCollector()
    raw_col = RawCollection(collector=collector, path_builder=pb)
    
    # 실제 수집 실행
    raw_res = raw_col.run(target_url)
    
    if raw_res.status == "fail":
        print(f"!!! [Stage 1 실패] 수집 중 오류 발생: {raw_res.reason_code}")
        # Stage 5로 넘겨서 분석
        classifier = FailClassification()
        classifier.classify_and_log(stage="raw", reason_code=raw_res.reason_code, entity_id=target_url, category_cd="CA01")
        return

    print(f"OK: 원시 데이터 파일 저장 완료 -> {raw_res.file_path}")

    # --- [Stage 2] Parsing 시도 ---
    # 다이닝코드 메인 페이지에는 '.tit' 등의 셀렉터가 없을 가능성이 높음 (의도적인 실패 테스트)
    print("\n[Stage 2] 파싱 시도 (셀렉터 매칭 테스트)")
    parsing_stage = CandidateParsing(path_builder=pb)
    parse_res = parsing_stage.run(raw_res.file_path)
    
    if parse_res["status"] == "fail":
        print(f"!!! [Stage 2 실패] 파싱 오류 발생: {parse_res['reason_code']}")
        # --- [Stage 5] Fail Classification 연동 ---
        print("\n[Stage 5] 실패 분석 및 대응 결정...")
        classifier = FailClassification() 
        # 재시도 횟수 0회로 투입
        ledger = classifier.classify_and_log(
            stage="parsing", 
            reason_code=parse_res["reason_code"], 
            entity_id=target_url,
            category_cd="CA01",
            reason_detail=parse_res.get("reason_detail")
        )
        print(f"결정된 후속 조치(Action): {ledger.action}")
        print("-> 'retry'일 경우 내일 다시 수집하고, 'drop'인 경우 로그만 남기고 종료합니다.")
        return

    print("OK: 파싱 성공!")
    
if __name__ == "__main__":
    run_diningcode_demo()
