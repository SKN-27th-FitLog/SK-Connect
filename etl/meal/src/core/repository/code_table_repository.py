from typing import Dict, Any, Optional, List
from sqlalchemy import text
from src.core.repository.database import DatabaseManager, db_manager
from src.core.constants import (
    QUERY_SELECT_ALL_ADDRESS_CODES,
    QUERY_SELECT_ALL_SHOP_CODES
)
import logging

logger = logging.getLogger(__name__)

class CodeTableRepository:
    """
    DB 코드 테이블을 조회하고 메모리 캐싱을 수행하는 클래스.
    설계안 7장(코드 테이블 중심 설계) 준수.
    """
    def __init__(self, db: DatabaseManager = db_manager):
        self.db = db
        # Handler Scope 캐시
        self._address_cache: Dict[str, Dict[str, Any]] = {}
        self._shop_code_cache: Dict[str, str] = {}
        self._is_loaded = False

    def preload(self):
        """
        Handler 시작 시 모든 코드 테이블을 캐시에 로드.
        설계안 7.5 준수.
        """
        if self._is_loaded:
            return

        with self.db.get_session() as session:
            # 1. 주소 코드 로드
            address_rows = session.execute(text(QUERY_SELECT_ALL_ADDRESS_CODES)).mappings().all()
            for row in address_rows:
                # province + city + district 조합을 키로 하여 코드 검색 가능하도록 구성 (예시)
                full_addr_key = f"{row['province']} {row['city']} {row.get('district', '')}".strip()
                self._address_cache[full_addr_key] = dict(row)
                # 코드 자체로도 검색 가능하게 저장
                self._address_cache[row['address_cd']] = dict(row)

            # 2. 업종(Shop) 코드 로드
            shop_rows = session.execute(text(QUERY_SELECT_ALL_SHOP_CODES)).mappings().all()
            for row in shop_rows:
                self._shop_code_cache[row['name']] = row['code']
                self._shop_code_cache[row['code']] = row['code']

        self._is_loaded = True
        logger.info(f"Code Table Preloaded: {len(self._address_cache)} addresses, {len(self._shop_code_cache)} shop codes.")

    def get_address_info(self, key: str) -> Optional[Dict[str, Any]]:
        """명칭 또는 코드로 주소 정보 조회"""
        if not self._is_loaded:
            self.preload()
        return self._address_cache.get(key)

    def get_shop_code(self, key: str) -> Optional[str]:
        """명칭 또는 코드로 업종 코드 조회"""
        if not self._is_loaded:
            self.preload()
        return self._shop_code_cache.get(key)

    def clear_cache(self):
        """실행 종료 시 폐기 (설계안 7.5)"""
        self._address_cache.clear()
        self._shop_code_cache.clear()
        self._is_loaded = False

# 전역 Repository 인스턴스 (필요 시 Handler 내부에서 초기화)
code_repo = CodeTableRepository()
