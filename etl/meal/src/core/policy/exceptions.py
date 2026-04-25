from typing import Optional, Any, Dict
from src.core.policy.reason_code import ReasonCode

class BasePipelineException(Exception):
    """
    파이프라인의 모든 예외의 최상위 클래스.
    설계안 3.2 준수: 실패 의미만 정의하며 정책(action, severity 등)은 가지지 않음.
    """
    def __init__(
        self, 
        reason_code: ReasonCode, 
        stage: str, 
        entity_type: str, 
        detail: str = "",
        entity_ref: Optional[Dict[str, Any]] = None
    ):
        self.reason_code = reason_code
        self.stage = stage
        self.entity_type = entity_type
        self.detail = detail
        self.entity_ref = entity_ref or {}
        
        message = f"[{stage}] {reason_code.name} - {entity_type}: {detail}"
        super().__init__(message)

class NetworkException(BasePipelineException):
    """네트워크 또는 인프라 관련 예외"""
    pass

class ScraperException(BasePipelineException):
    """스크래핑 과정에서의 구조적 실패 (Selector 등)"""
    pass

class ValidationException(BasePipelineException):
    """데이터 정규화 및 검증 실패"""
    pass

class LoadException(BasePipelineException):
    """DB 적재 과정에서의 실패"""
    pass

class DedupConflictException(BasePipelineException):
    """DEDUP 충돌 발생 시 예외"""
    pass

class UndefinedCodeException(BasePipelineException):
    """지정되지 않은 식별 불가 코드(예: UNKNOWN 주소) 또는 참조 무결성 위반 시 예외"""
    pass
