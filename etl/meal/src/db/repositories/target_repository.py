from typing import List, Dict, Any
from .base_repository import BaseRepository
from ..queries.store_queries import StoreQueries

class TargetRepository(BaseRepository):
    """
    수집 대상(Target) 추출 및 상태 확인을 담당하는 리포지토리입니다.
    """

    def get_already_loaded_urls(self, category_cd: str) -> List[str]:
        """
        이미 성공적으로 적재된 가게들의 목록을 조회합니다.
        (source_url 컬럼 부재로 인해 당분간 빈 리스트 반환하여 전체 수집 유도)
        """
        try:
            # 쿼리가 유효한 경우에만 실행 (SELECT_LOADED_STORE_NAMES 등으로 대체 가능)
            if hasattr(StoreQueries, 'SELECT_LOADED_STORE_NAMES'):
                rows = self.execute(StoreQueries.SELECT_LOADED_STORE_NAMES, (category_cd,))
                # URL 대신 이름 기반 필터링이 필요할 경우 여기서 처리
                return [] 
            return []
        except Exception:
            return []
