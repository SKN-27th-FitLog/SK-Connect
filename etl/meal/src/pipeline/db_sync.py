import json
from typing import Dict, Any
from .base_stage import BaseStage
from ..core.file_manager import logger
from ..db.repositories.store_repository import StoreRepository
from ..db.models.store_models import NormalizedStore

class DatabaseSync(BaseStage):
    """
    Stage 4: Database Sync
    정규화된 데이터를 DB(maps, shop)에 트랜잭션 단위로 최종 적재합니다.
    """
    
    def __init__(self, repository: StoreRepository):
        super().__init__("Database Sync")
        self.repository = repository

    def _execute(self, normalized_file_path: str) -> Dict[str, Any]:
        """
        단일 Normalized 파일을 읽어 DB에 적재합니다.
        """
        logger.info(f"--- [Stage 4] Syncing to DB: {normalized_file_path}")
        
        # 1. Normalized 데이터 로드
        try:
            with open(normalized_file_path, "r", encoding="utf-8") as f:
                line = f.readline()
                if not line: return {"status": "fail", "reason": "EMPTY_FILE"}
                data = json.loads(line)
                normalized = NormalizedStore(**data)
        except Exception as e:
            logger.error(f"!!! [Stage 4] Failed to load normalized data: {e}")
            return {"status": "fail", "reason_code": "NORMALIZED_LOAD_ERROR"}

        # 2. DB 적재용 데이터 매핑
        # 모델 데이터에서 DB 컬럼 규격에 맞는 딕셔너리로 변환
        db_data = {
            "name": normalized.normalized_name, # 정규화된 상호명 사용
            "category_cd": normalized.category_cd,
            "address_cd": normalized.category_cd[:4], # 예시: 주소 코드가 카테고리 기점일 경우
            "address_detail": normalized.normalized_address,
            "latitude": normalized.latitude or 0.0,
            "longitude": normalized.longitude or 0.0,
            "shop_cd": normalized.source_platform,
            "rating": normalized.rating or 0.0
        }

        # 3. DB 저장 실행 (트랜잭션 보장)
        try:
            # Repository에서 @db_transaction 처리됨
            shop_id = self.repository.save_store(db_data)
            logger.info(f"--- [Stage 4] Successfully saved to DB (Shop ID: {shop_id})")
            
            return {
                "status": "success",
                "shop_id": shop_id,
                "canonical_url": normalized.canonical_url
            }
            
        except Exception as e:
            logger.error(f"!!! [Stage 4] Database insertion failed: {e}")
            return {
                "status": "fail",
                "reason_code": "DB_INSERTION_ERROR",
                "reason_detail": str(e)
            }
