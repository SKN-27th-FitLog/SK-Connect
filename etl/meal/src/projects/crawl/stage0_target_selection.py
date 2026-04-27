import logging
from typing import List, Dict, Any, Set

from src.core.base_stage import BaseStage
from src.core.repository.code_table_repository import CodeTableRepository, code_repo
from src.core.repository.store_repository import StoreRepository, store_repo
from src.core.repository.fail_repository import FailRepository, fail_repo
from src.core.repository.source_pool_provider import SourcePoolProvider, source_pool_provider

class Stage0TargetSelection(BaseStage):
    """
    [설계안 6.2 일치] - Daily Target Selection 고도화.
    원칙: 
    1. retry 대상 우선 포함 (FailRepository)
    2. 기 수집 성공 대상 제외 (StoreRepository dedup_keys)
    3. 부족분 신규 후보 보충 (SourcePoolProvider)
    4. 최종 100건 구성 후 검색 쿼리 생성
    """
    NAME = "target_selection"

    def __init__(
        self, 
        code_repo: CodeTableRepository = code_repo,
        store_repo: StoreRepository = store_repo,
        fail_repo: FailRepository = fail_repo,
        source_pool: SourcePoolProvider = source_pool_provider,
        target_count: int = 100
    ):
        super().__init__(self.NAME)
        self.code_repo = code_repo
        self.store_repo = store_repo
        self.fail_repo = fail_repo
        self.source_pool = source_pool
        self.target_count = target_count

    def execute(self, category_cd: str, platform: str = "DiningCode") -> tuple[List[Dict[str, Any]], str]:
        self.code_repo.preload()
        selected_targets = []
        
        # 1. 기 성공 적재 데이터의 dedup_keys 조회 (중복 제거용)
        existing_keys: Set[str] = self.store_repo.find_success_loaded_dedup_keys(category_cd)
        self.logger.info(f"Loaded {len(existing_keys)} existing dedup keys for {category_cd}")

        # 2. Retry 대상 우선 포함 (설계안 6.2)
        retry_pool = self.fail_repo.get_retry_targets(category_cd, platform)
        for item in retry_pool:
            if len(selected_targets) >= self.target_count:
                break
            selected_targets.append(self._build_target_item(item, category_cd, platform, is_retry=True))
        
        self.logger.info(f"Included {len(selected_targets)} retry targets.")

        # 3. 부족분 신규 후보 보충 및 중복 제외
        if len(selected_targets) < self.target_count:
            candidates = self.source_pool.get_candidates(category_cd)
            for cand in candidates:
                if len(selected_targets) >= self.target_count:
                    break
                
                # 중복 판정 (설계안 10.2 방식 유사 키 생성)
                addr_cd = cand['address_cd']
                addr_info = self.code_repo.get_address_info(addr_cd)
                if not addr_info: continue
                
                # 가상 dedup_key 생성
                candidate_key = f"{addr_info['name'].replace(' ', '')}|{addr_cd}"
                
                if self.store_repo.is_duplicated(candidate_key, existing_keys):
                    continue
                
                selected_targets.append(self._build_target_item(cand, category_cd, platform))

        self.logger.info(f"Final targeting complete: {len(selected_targets)} items for Stage 1.")
        return selected_targets, self.source_pool.seed_file

    def _build_target_item(self, source: Dict[str, Any], category_cd: str, platform: str, is_retry: bool = False) -> Dict[str, Any]:
        """선정된 대상으로부터 Stage 1 수집용 타겟 스펙 생성"""
        addr_cd = source.get("address_cd", source.get("raw_info", {}).get("address_cd"))
        addr_info = self.code_repo.get_address_info(addr_cd)
        shop_info_name = self.code_repo.get_shop_code_name(category_cd)
        
        return {
            "address_cd": addr_cd,
            "category_cd": category_cd,
            "address_name": addr_info['name'] if addr_info else "Unknown",
            "category_name": shop_info_name or "Unknown",
            "source_platform": platform,
            "search_query": f"{addr_info['name'] if addr_info else ''} {shop_info_name or ''}".strip(),
            "is_retry": is_retry,
            "retry_count": source.get("retry_count", 0)
        }
