from typing import List, Dict, Any
from .base_repository import BaseRepository
from ..queries.store_queries import (
    SELECT_LOADED_STORE_URLS, 
    SELECT_RETRY_TARGETS, 
    SELECT_NEW_CANDIDATES
)

class TargetRepository(BaseRepository):
    """
    수집 대상(Target) 추출 및 상태 확인을 담당하는 리포지토리입니다.
    """

    def get_already_loaded_urls(self, category_cd: str) -> List[str]:
        """이미 성공적으로 적재된 가게들의 URL 목록을 조회합니다."""
        rows = self.execute(SELECT_LOADED_STORE_URLS, (category_cd,))
        return [row['canonical_url'] for row in rows] if rows else []

    def get_retry_targets(self, category_cd: str) -> List[Dict[str, Any]]:
        """실패한 내역 중 재시도가 필요한 대상을 조회합니다."""
        rows = self.execute(SELECT_RETRY_TARGETS, (category_cd,))
        return rows if rows else []

    def get_new_candidates(self, category_cd: str, limit: int) -> List[Dict[str, Any]]:
        """소스 풀로부터 신규 수집 후보를 추출합니다."""
        if limit <= 0:
            return []
        rows = self.execute(SELECT_NEW_CANDIDATES, (category_cd, limit))
        return rows if rows else []
