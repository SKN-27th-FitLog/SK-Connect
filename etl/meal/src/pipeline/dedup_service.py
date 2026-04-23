from typing import Dict, Any, Optional
from ..repositories.store_repository import StoreRepository
from ..core.file_manager import logger

class DedupService:
    """
    Stage 3: Deduplication Service
    설계서 v4의 계층적 중복 제거 규칙을 실체화합니다.
    우선순위:
    1) canonical_url
    2) normalized_name + normalized_address
    3) source_platform + source_internal_id (fallback)
    """
    
    def __init__(self, store_repo: StoreRepository):
        self.repo = store_repo
        self.rule_version = "v1" # 설계서 v4 요구사항: 버전 관리 필수

    def get_dedup_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        데이터의 중복 여부를 확인하고 판정 지점과 키 정보를 반환합니다.
        """
        # 1순위: canonical_url
        c_url = data.get("canonical_url")
        if c_url:
            if self.repo.exists_by_url(c_url):
                return {
                    "is_duplicate": True, 
                    "type": "canonical_url", 
                    "value": c_url,
                    "rule_version": self.rule_version
                }

        # 2순위: 정규화된 상호명 + 정규화된 주소
        # (v4 설계서는 이미 validation/normalization이 완료된 상태를 가정함)
        n_name = data.get("normalized_name") or data.get("name")
        n_addr = data.get("normalized_address") or data.get("address")
        if n_name and n_addr:
            if self.repo.exists_by_name_address(n_name, n_addr):
                return {
                    "is_duplicate": True, 
                    "type": "name_address", 
                    "value": f"{n_name}|{n_addr}",
                    "rule_version": self.rule_version
                }

        # 3순위: 플랫폼 고유 ID (Fallback)
        platform = data.get("source_platform")
        internal_id = data.get("source_internal_id")
        if platform and internal_id:
            if hasattr(self.repo, 'exists_by_platform_id'): # 리포지토리 메서드 존재 시 확인
                if self.repo.exists_by_platform_id(platform, internal_id):
                    return {
                        "is_duplicate": True, 
                        "type": "platform_id", 
                        "value": f"{platform}|{internal_id}",
                        "rule_version": self.rule_version
                    }

        # 신규 데이터로 판정
        return {
            "is_duplicate": False, 
            "type": None, 
            "value": None,
            "rule_version": self.rule_version
        }
