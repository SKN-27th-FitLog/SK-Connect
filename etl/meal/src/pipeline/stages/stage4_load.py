from typing import List, Dict, Any
from sqlalchemy import text
from src.pipeline.stages.base_stage import BaseStage
from src.core.repository.database import db_manager
from src.core.repository.code_table_repository import CodeTableRepository, code_repo
from src.core.constants import QUERY_UPSERT_STORE
from datetime import datetime
import logging

class Stage4Load(BaseStage):
    """
    설계안 2.2, 17, 22장 준수 - Load Stage.
    정규화된 데이터를 DB에 적재하며 원자적 Upsert 제공.
    """
    def __init__(self, code_repository: CodeTableRepository = code_repo):
        super().__init__("load")
        self.code_repo = code_repository

    def _verify_integrity(self, store_data: Dict[str, Any]) -> bool:
        """
        설계안 220 준수 - 적재 직전 코드 테이블 참조 무결성 재검증.
        """
        # 캐싱된 코드 데이터를 다시 확인
        addr_cd = store_data.get("address_cd")
        shop_cd = store_data.get("shop_cd")
        
        if not self.code_repo.get_address_info(addr_cd):
            self.logger.error(f"Integrity Check Failed: Invalid address_cd {addr_cd}")
            return False
            
        # shop_cd 검증 로직 등 추가 가능
        return True

    def execute(self, normalized_data: List[Dict[str, Any]], batch_id: str, category_cd: str) -> List[Dict[str, Any]]:
        """
        데이터 적재 수행.
        설계안 17장: Store/Menu/Review 트랜잭션 분리.
        """
        load_results = []
        now = datetime.now()
        
        # 코드 테이블 최신화
        self.code_repo.preload()
        
        for record in normalized_data:
            store_data = record.get("store", {})
            entity_id = store_data.get("entity_id")
            
            # 1. 무결성 재검증 (설계안 7.5)
            if not self._verify_integrity(store_data):
                load_results.append({
                    "entity_id": entity_id,
                    "status": "fail",
                    "reason_code": "INTEGRITY_CHECK_FAILED"
                })
                continue

            try:
                with db_manager.get_session() as session:
                    # 2. Store Upsert (설계안 17: 1 트랜잭션)
                    # pydantic 모델에서 dict로 변환된 값 사용
                    session.execute(text(QUERY_UPSERT_STORE), store_data)
                    session.commit()
                    
                    # 3. Menu/Review (별도 트랜잭션 - 여기서는 단순 루프 내 처리)
                    # 실제 운영 환경에서는 독립된 로더나 서비스 호출 권장
                    menus = record.get("menus", [])
                    reviews = record.get("reviews", [])
                    
                    # (생략) 메뉴/리뷰 적재 로직 - 추후 확장
                    
                    load_results.append({
                        "entity_id": entity_id,
                        "status": "success",
                        "store_id": store_data.get("dedup_key") # dedup_key를 store_id 대용으로 사용 가능
                    })
                    
            except Exception as e:
                self.logger.error(f"Database Load Failed for {entity_id}: {str(e)}")
                load_results.append({
                    "entity_id": entity_id,
                    "status": "fail",
                    "reason_code": "DB_LOAD_ERROR",
                    "detail": str(e)
                })

        self.logger.info(f"Loaded {len([r for r in load_results if r['status']=='success'])} records to DB.")
        return load_results
