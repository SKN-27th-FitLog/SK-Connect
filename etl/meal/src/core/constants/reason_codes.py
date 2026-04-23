from enum import Enum

class FailAction(Enum):
    """실패 시 후속 조치 정의"""
    RETRY = "retry"             # 다음 배치에서 재시도
    REPROCESS = "reprocess"     # 파서/로직 수정 후 재처리 필요
    DROP = "drop"               # 수집 대상에서 제외
    LOAD_WITH_WARNING = "load_with_warning" # 경고와 함께 적재 진행
    ALERT_ONLY = "alert_only"   # 적재 실패 무시, 알림만 생성

class ReasonCode(Enum):
    """에러 원인 코드 및 기본 액션 정의"""
    
    # Stage 1: Raw Collection
    NETWORK_ERROR = ("S101", FailAction.RETRY)
    TIMEOUT = ("S102", FailAction.RETRY)
    RATE_LIMITED = ("S103", FailAction.RETRY)
    INVALID_URL = ("S104", FailAction.DROP)
    BLOCKED_SOURCE = ("S105", FailAction.DROP)
    
    # Stage 2: Candidate Parsing
    SELECTOR_MISMATCH = ("S201", FailAction.REPROCESS)
    EMPTY_EXTRACTION = ("S202", FailAction.REPROCESS)
    NOT_RESTAURANT = ("S203", FailAction.DROP)
    
    # Stage 3: Validation & Dedup
    MISSING_REQUIRED_FIELD = ("S301", FailAction.REPROCESS)
    DEDUP_KEY_FAIL = ("S302", FailAction.REPROCESS)
    SCHEMA_VIOLATION = ("S303", FailAction.DROP)
    
    # Stage 4: Load (SQL/DB)
    DB_CONNECTION_ERROR = ("S401", FailAction.RETRY)
    DUPLICATE_MAPS = ("S402", FailAction.DROP)
    LOAD_FAILED_CRITICAL = ("S403", FailAction.RETRY) # Maps 실패 등
    LOAD_FAILED_MINOR = ("S404", FailAction.LOAD_WITH_WARNING) # Menu 등
    
    # System
    UNKNOWN_ERROR = ("S999", FailAction.ALERT_ONLY)

    def __init__(self, code, default_action):
        self.code = code
        self.default_action = default_action
