import logging
from typing import Set, Dict, Any, Optional
from sqlalchemy import text
from src.core.repository.database import DatabaseManager, db_manager

logger = logging.getLogger("core.repository")

class StoreRepository:
    """
    [구현 계획 1 반영] - Store 레포지토리.
    성공 적재 데이터의 dedup_key 조회 및 중복 판정 지원.
    """
    def __init__(self, db: DatabaseManager = db_manager):
        self.db = db

    def find_success_loaded_dedup_keys(self, category_cd: str) -> Set[str]:
        """
        설계안 10장 준수 - 이미 적재된 Store의 dedup_key 목록을 반환.
        """
        # 주: 실제 스키마에 dedup_key 컬럼이 있다고 가정하거나, 
        # maps 테이블의 name, address 정보를 조합하여 조회.
        # 여기서는 name + address_cd 조합을 기본 키로 시뮬레이션.
        query = """
            SELECT name, address_cd
            FROM maps
            WHERE category_cd = :category_cd
        """
        dedup_keys = set()
        try:
            with self.db.get_session() as session:
                result = session.execute(text(query), {"category_cd": category_cd})
                for row in result:
                    # 설계안 10.2 준수 (name_address 방식 예시)
                    name = row.name.replace(" ", "")
                    key = f"{name}|{row.address_cd}"
                    dedup_keys.add(key)
        except Exception as e:
            logger.error(f"Failed to fetch success loaded dedup keys: {e}")
            
        return dedup_keys

    def is_duplicated(self, target_dedup_key: str, existing_keys: Set[str]) -> bool:
        """후보 target과 기존 성공 데이터 간의 중복 여부 판정 보조"""
        return target_dedup_key in existing_keys

    def find_snapshot_by_dedup_key(self, dedup_key: str) -> Optional[Dict[str, Any]]:
        """
        Design 31: SnapshotRepository 역할.
        Hash 컬럼이 아직 없는 DB에서도 Stage 3 실행을 막지 않도록 조회 실패는 신규 데이터로 취급한다.
        """
        query = """
            SELECT
                s.shop_id AS store_id,
                s.store_content_hash,
                s.menu_content_hash,
                s.review_content_hash,
                s.image_content_hash,
                s.updated_at AS last_updated_at,
                s.last_checked_at
            FROM shop s
            JOIN maps m ON m.map_id = s.map_id
            WHERE s.dedup_key = :dedup_key OR m.canonical_url = :dedup_key
            LIMIT 1
        """
        try:
            with self.db.get_session() as session:
                row = session.execute(text(query), {"dedup_key": dedup_key}).mappings().first()
                return dict(row) if row else None
        except Exception as e:
            logger.debug(f"Snapshot hash lookup skipped for dedup_key={dedup_key}: {e}")
            return None

# 전역 인스턴스 등록 (Registry 활용 가능)
store_repo = StoreRepository()
