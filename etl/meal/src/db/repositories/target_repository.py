from typing import List, Dict, Any
from .base_repository import BaseRepository
from ..queries.store_queries import StoreQueries

class TargetRepository(BaseRepository):
    """
    수집 대상(Target) 추출 및 상태 확인을 담당하는 리포지토리입니다.
    """

    def get_already_loaded_urls(self, category_cd: str) -> List[str]:
        """이미 성공적으로 적재된 가게들의 URL 목록을 조회합니다."""
        rows = self.execute(StoreQueries.SELECT_LOADED_STORE_URLS, (category_cd,))
        return [row['canonical_url'] for row in rows] if rows else []

    # TODO: fail_ledger, store_source_pool 테이블이 없으므로 
    # 재시도 대상 및 신규 후보 추출 로직은 파일(CSV) 기반으로 전환 필요
