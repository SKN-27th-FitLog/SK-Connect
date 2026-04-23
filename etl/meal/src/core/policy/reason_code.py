from enum import Enum, auto

class ReasonCode(Enum):
    """
    ETL 파이프라인 전반에서 발생하는 실패의 원인을 정의하는 Enum.
    설계안 7.4 및 14.1 준수.
    """
    # 1. Network & Infrastructure
    NETWORK_ERROR = auto()
    PROXY_ERROR = auto()
    TIMEOUT = auto()
    
    # 2. Site/Platform Specific
    SELECTOR_MISMATCH = auto()
    BOT_DETECTED = auto()
    NOT_FOUND = auto()      # 대상 페이지가 없음 (404 등)
    INVALID_URL = auto()
    
    # 3. Data Integrity & Business Logic
    INVALID_DATA_FORMAT = auto()
    MISSING_REQUIRED_FIELD = auto()
    NOT_RESTAURANT_ENTITY = auto() # 음식점 엔티티가 아님
    
    # 4. Dedup & Conflict
    CONFLICTING_DEDUP_SIGNALS = auto() # 설계안 10. 충돌 시 사용
    
    # 5. Database & System
    DB_CONNECTION_ERROR = auto()
    DB_CONSTRAINT_VIOLATION = auto()
    UNDEFINED_CODE_DETECTED = auto() # 설계안 16. reprocess 승격 후보
    
    # 6. Others
    UNKNOWN_ERROR = auto()
    INTERNAL_PIPELINE_ERROR = auto()

    def __str__(self):
        return self.name
