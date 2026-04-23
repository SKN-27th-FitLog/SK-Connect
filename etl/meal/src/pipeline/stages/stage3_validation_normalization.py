from typing import List, Dict, Any, Optional
from src.pipeline.stages.base_stage import BaseStage
from src.core.repository.code_table_repository import CodeTableRepository, code_repo
from src.core.storage.path_builder import HivePathBuilder
from src.core.storage.jsonl_writer import JsonlWriter
from src.core.models.models import StoreModel
from datetime import datetime
import hashlib

class Stage3ValidationNormalization(BaseStage):
    """
    설계안 2.2, 7.2, 10장 준수 - Validation & Normalization Stage.
    데이터 정규화, 주소 코드 분리, Dedup Key 생성 수행.
    """
    def __init__(self, code_repository: CodeTableRepository = code_repo):
        super().__init__("validation_normalization")
        self.code_repo = code_repository

    def _normalize_address(self, full_address: str) -> tuple[str, str]:
        """
        주소 정규화 (설계안 7.2).
        address_cd + address_detail 분리.
        """
        # 설계안: 코드 테이블에 정의된 주소 범위를 찾아 address_cd로 저장하고 나머지는 detail로.
        # 실제 구현은 긴 명칭부터 매칭하는 방식 등이 필요하나 여기서는 기초 로직 구현.
        
        # 예: "서울특별시 강남구 테헤란로 123" -> address_cd="LA01"(서울 강남), detail="테헤란로 123"
        # Repository의 캐시된 데이터를 순회하며 매칭 시도
        
        best_match_cd = "UNKNOWN"
        detail = full_address
        
        # 간단한 매칭 예시 (실제 서비스에서는 더 정교한 토큰 기반 매칭 권장)
        for addr_key, info in self.code_repo._address_cache.items():
            if full_address.startswith(addr_key):
                best_match_cd = info['address_cd']
                detail = full_address.replace(addr_key, "").strip()
                break
                
        return best_match_cd, detail

    def _generate_dedup_key(self, shop_data: Dict[str, Any], canonical_url: Optional[str]) -> tuple[str, str]:
        """
        Dedup Key 생성 (설계안 10장).
        우선순위: 1. canonical_url, 2. name+address, 3. platform+id
        """
        if canonical_url:
            return canonical_url, "canonical_url"
            
        name = shop_data.get("name", "").replace(" ", "")
        address = shop_data.get("full_address", "").replace(" ", "")
        if name and address:
            key_val = f"{name}|{address}"
            # 해시 처리하거나 원문 사용 (설계안 예시: 맛있는초밥본점|서울특별시강남구테헤란로123)
            return key_val, "name_address"
            
        platform = shop_data.get("source_platform", "")
        pid = shop_data.get("source_internal_id", "")
        return f"{platform}|{pid}", "platform_id"

    def execute(self, candidates: List[Dict[str, Any]], batch_id: str, category_cd: str) -> List[Dict[str, Any]]:
        """
        Candidate 데이터를 정규화하여 Normalized JSONL 생성.
        """
        normalized_data = []
        now = datetime.now()
        
        # 코드 테이블 프리로드 (설계안 7.5)
        self.code_repo.preload()
        
        for cand in candidates:
            try:
                shop_raw = cand.get("shop", {})
                
                # 1. 주소 정규화
                addr_cd, addr_detail = self._normalize_address(shop_raw.get("full_address", ""))
                
                # 2. Dedup Key 생성
                dedup_key, dedup_key_type = self._generate_dedup_key(shop_raw, shop_raw.get("canonical_url"))
                
                # 3. Store 모델 생성 및 검증
                # 설계안 13장 entity_ref 포함
                store = StoreModel(
                    entity_id=cand.get("entity_id", ""),
                    entity_ref=cand.get("entity_ref", {}),
                    name=shop_raw.get("name", "Unknown"),
                    shop_cd=self.code_repo.get_shop_code(category_cd) or "UNKNOWN",
                    address_cd=addr_cd,
                    address_detail=addr_detail,
                    source_platform=shop_raw.get("source_platform", ""),
                    source_internal_id=shop_raw.get("source_internal_id", ""),
                    dedup_key=dedup_key,
                    dedup_key_type=dedup_key_type,
                    canonical_url=shop_raw.get("canonical_url")
                )
                
                normalized_record = {
                    "store": store.model_dump(),
                    "menus": cand.get("menus", []),
                    "reviews": cand.get("reviews", []),
                    "normalized_at": now.isoformat()
                }
                normalized_data.append(normalized_record)
                
            except Exception as e:
                self.logger.error(f"Normalization failed for {cand.get('entity_id')}: {str(e)}")
        
        # 4. Normalized 결과 저장 (JSONL)
        normalized_path = HivePathBuilder.build_path(
            process="normalized", service="shop", category_cd=category_cd,
            stage=self.stage_name, batch_id=batch_id, status="success", dt=now
        )
        filename = HivePathBuilder.build_filename(extension="jsonl", dt=now)
        JsonlWriter.write(normalized_path, filename, normalized_data)
        
        self.logger.info(f"Normalized {len(normalized_data)} records for batch {batch_id}")
        return normalized_data
