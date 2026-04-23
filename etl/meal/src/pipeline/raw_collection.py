import os
import uuid
from .base_stage import BaseStage
from ..core.file_manager import logger
from ..services.collectors.http_collector import HttpCollector
from ..db.models.raw_models import RawCollectionResult
from ..core.storage.hive_path_builder import HivePathBuilder

class RawCollection(BaseStage):
    """
    Stage 1: Raw Collection
    대상 URL로부터 원시 데이터를 수집하고 이를 파일로 보존(Capture)합니다.
    """
    
    def __init__(self, collector=None, path_builder=None):
        super().__init__("Raw Collection")
        self.collector = collector or HttpCollector()
        self.path_builder = path_builder or HivePathBuilder()

    def _execute(self, url: str) -> RawCollectionResult:
        """
        BaseStage 규약에 따른 핵심 로직 구현 (단일 URL 수집 및 저장)
        """
        logger.info(f"--- [Stage 1] Collecting raw data from: {url}")
        
        # 1. 실제 수집 수행
        collect_res = self.collector.collect(url)
        
        if collect_res["status"] == "fail":
            return RawCollectionResult(
                url=url,
                status="fail",
                reason_code=collect_res.get("reason_code", "UNKNOWN_COLLECT_FAIL"),
                reason_detail=collect_res.get("reason_detail")
            )
            
        result = RawCollectionResult(
            url=url,
            status="success",
            raw_content=collect_res["raw_content"],
            http_status=collect_res["http_status"]
        )
        
        # 2. 파일 보존 (Stateless를 위한 증거 저장)
        # 서비스 명은 기본 shop으로 설정 (필요시 컨텍스트 연동)
        self._save_raw_file(result, service="shop")
        
        return result

    def _save_raw_file(self, result: RawCollectionResult, service: str):
        """
        수집된 내용을 Hive 경로 정책에 맞게 저장합니다.
        """
        try:
            # Hive 경로 생성 (status=success)
            dir_path = self.path_builder.build(
                stage="raw", 
                status="success", 
                service=service
            )
            
            if not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
            
            # 파일명 생성 (Timestamp + UUID)
            ts = result.collected_at.strftime("%H%M%S")
            unique_id = uuid.uuid4().hex[:6]
            file_name = f"{ts}_{unique_id}.{result.file_extension}"
            
            full_path = f"{dir_path}/{file_name}"
            
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(result.raw_content)
                
            result.file_path = full_path
            logger.info(f"--- [Stage 1] Raw data captured: {full_path}")
            
        except Exception as e:
            logger.error(f"!!! [Stage 1] Failed to save raw file: {e}")
            result.status = "fail"
            result.reason_code = "FILE_SAVE_ERROR"
            result.reason_detail = str(e)
