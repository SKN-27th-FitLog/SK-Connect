from ..repositories.store_repository import StoreRepository
from ..utils.decorators import trace_stage, db_transaction
from ..core.file_manager import logger

class LoadPipeline:
    """
    Stage 4: Load
    정규화된 데이터를 DB에 최종 적재합니다.
    """
    
    def __init__(self, db_client, store_repo: StoreRepository):
        self.db = db_client
        self.repo = store_repo

    @trace_stage("Data Loading")
    def run(self, batch_id: str, normalized_data: list):
        """
        데이터 적재 프로세스를 전체적으로 관장합니다.
        """
        success_count = 0
        fail_count = 0
        
        for item in normalized_data:
            try:
                # 1. 중복 체크는 이미 Stage 3에서 수행되었다고 가정
                # 2. 적재 수행 (내부적으로 db_transaction 사용)
                shop_id = self.repo.save_store(item)
                success_count += 1
                logger.info(f"--- [Load] Successfully loaded store: {item['name']} (ID: {shop_id})")
            except Exception as e:
                fail_count += 1
                logger.error(f"!!! [Load] Failed to load store: {item.get('name')} - {e}")
                
        return {
            "batch_id": batch_id,
            "summary": {
                "success_count": success_count,
                "fail_count": fail_count
            }
        }
