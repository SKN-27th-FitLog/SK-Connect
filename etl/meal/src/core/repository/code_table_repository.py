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
    DB 코드 테이블(codeT)을 조회하고 메모리 캐싱을 수행하는 클래스.
    설계안 7장(코드 테이블 중심 설계) 준수.
    """
    def __init__(self, db: DatabaseManager = db_manager):
        self.db = db
        # Handler Scope 캐시
        self._address_cache: Dict[str, Dict[str, Any]] = {}
        self._shop_code_cache: Dict[str, str] = {}
        self._shop_name_cache: Dict[str, str] = {}
        self._is_loaded = False

    def preload(self):
        """
        Handler 시작 시 모든 코드 테이블을 캐시에 로드.
        """
        if self._is_loaded:
            return

        try:
            with self.db.get_session() as session:
                # 1. 주소 코드 로드 (L-xxx 계열)
                address_rows = session.execute(text(QUERY_SELECT_ALL_ADDRESS_CODES)).mappings().all()
                for row in address_rows:
                    # 명칭(name) 또는 코드(address_cd)로 검색 가능하게 저장
                    self._address_cache[row['name']] = dict(row)
                    self._address_cache[row['address_cd']] = dict(row)

                # 2. 업종(Shop) 코드 로드 (S-xxx 계열)
                shop_rows = session.execute(text(QUERY_SELECT_ALL_SHOP_CODES)).mappings().all()
                for row in shop_rows:
                    self._shop_code_cache[row['name']] = row['code']
                    self._shop_code_cache[row['code']] = row['code']
                    self._shop_name_cache[row['code']] = row['name']

            self._is_loaded = True
            logger.info(f"Code Table(codeT) Preloaded: {len(self._address_cache)} addresses, {len(self._shop_code_cache)} shop codes.")
        except Exception as e:
            logger.error(f"Failed to preload code table: {e}")

    def get_address_info(self, key: str) -> Optional[Dict[str, Any]]:
        """명칭 또는 코드로 주소 정보 조회"""
        if not self._is_loaded:
            self.preload()
        return self._address_cache.get(key)

    def get_all_addresses(self) -> Dict[str, Dict[str, Any]]:
        """전체 주소 정보 딕셔너리 반환"""
        if not self._is_loaded:
            self.preload()
        return self._address_cache

    def get_shop_code(self, key: str) -> Optional[str]:
        """명칭 또는 코드로 업종 코드 조회"""
        if not self._is_loaded:
            self.preload()
        return self._shop_code_cache.get(key)

    def get_shop_code_name(self, code: str) -> Optional[str]:
        """코드로 명칭 조회 (역방향)"""
        if not self._is_loaded:
            self.preload()
        # 캐시에 이미 코드가 키로도 저장되어 있다면 해당 값을 반환하거나 명칭 맵을 활용
        # 현재 구현상 _shop_code_cache에 'S-xxx': 'S-xxx'로 저장되므로 별도 name 맵이 필요할 수 있음
        # 단순화된 codeT 구조에서는 cd, name이 1:1 매칭되므로 preload 시 name_cache도 구축
        return self._shop_name_cache.get(code)

    def validate_references(self, record: Dict[str, Any]) -> bool:
        """
        데이터 레코드의 코드 참조 무결성을 검증합니다.
        (사용자 피드백 반영: 정규화 필드 우선, 누락 시 실패 처리)
        """
        store = record.get("store", {})
        
        # 1. 대상 코드 추출 (정규화 필드 우선순위 적용)
        addr_cd = store.get("normalized_address_cd") or store.get("address_cd")
        shop_cd = store.get("normalized_shop_cd") or store.get("shop_cd") or store.get("normalized_category_cd")
        
        # 2. 필수 값 누락 검증 (None 또는 빈 문자열인 경우 실패)
        if not addr_cd or not shop_cd:
            logger.warning(f"Reference Validation Failed: Missing code (addr_cd={addr_cd}, shop_cd={shop_cd})")
            return False
            
        # 3. 주소 코드 검증: UNKNOWN이 아닌 경우에만 캐시 존재 여부 확인
        if addr_cd != "UNKNOWN":
            if not self.get_address_info(addr_cd):
                logger.warning(f"Invalid address_cd detected: {addr_cd}")
                return False
                
        # 4. 업종 코드 검증: UNKNOWN이 아닌 경우에만 캐시 존재 여부 확인
        if shop_cd != "UNKNOWN":
            if not self.get_shop_code(shop_cd):
                logger.warning(f"Invalid shop_cd detected: {shop_cd}")
                return False
                
        return True

    def clear_cache(self):
        """실행 종료 시 폐기 (설계안 7.5)"""
        self._address_cache.clear()
        self._shop_code_cache.clear()
        self._shop_name_cache.clear()
        self._is_loaded = False

code_repo = CodeTableRepository()
