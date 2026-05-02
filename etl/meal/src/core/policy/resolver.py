from enum import Enum, auto
from typing import Dict, Any, Optional
from src.core.policy.reason_code import ReasonCode

class Action(Enum):
    """설계안 14.3 준수 - 실패에 대한 후속 조치 정의"""
    RETRY = auto()      # 다음 배치에 포함하여 재시도 (failcheck가 target_project별 dispatch 큐로 배분)
    REPROCESS = auto()  # 코드 수정 후 재처리가 필요한 경우 (Selector 등)
    DROP = auto()       # 영구 폐기
    WARN = auto()       # 종료하되 로그/운영 기록 남김
    CRITICAL = auto()   # 시스템 중단 등의 심각한 에러

class PolicyResolver:
    """
    설계안 7.3, 14.1, 15장 준수 - 정책 판단의 Source of Truth.
    reason_code + stage + retry_count 등을 기준으로 action을 결정.
    """
    
    def __init__(self, max_retries: int = 5):
        self.max_retries = max_retries
        # 기본 정책 매핑 (설계안 14.3 예시 반영)
        self._rules: Dict[str, Action] = {
            ReasonCode.NETWORK_ERROR.value: Action.RETRY,
            ReasonCode.TIMEOUT.value: Action.RETRY,
            ReasonCode.PROXY_ERROR.value: Action.RETRY,
            
            ReasonCode.SELECTOR_MISMATCH.value: Action.REPROCESS,
            ReasonCode.BOT_DETECTED.value: Action.RETRY,
            
            ReasonCode.INVALID_URL.value: Action.DROP,
            ReasonCode.NOT_RESTAURANT_ENTITY.value: Action.DROP,
            ReasonCode.NOT_FOUND.value: Action.DROP,
            
            ReasonCode.CONFLICTING_DEDUP_SIGNALS.value: Action.WARN,
            ReasonCode.UNDEFINED_CODE_DETECTED.value: Action.REPROCESS, # 설계안 16. reprocess 승격 후보
            ReasonCode.REFERENCE_INTEGRITY_VIOLATION.value: Action.REPROCESS,
            
            ReasonCode.DB_CONSTRAINT_VIOLATION.value: Action.WARN,
            ReasonCode.INVALID_DATA_FORMAT.value: Action.WARN,
        }

    def resolve(
        self, 
        reason_code_str: str, 
        stage: str, 
        retry_count: int = 0
    ) -> Action:
        """
        최종 action 결정 로직.
        설계안 14.2, 14.3 반영.
        """
        base_action = self._rules.get(reason_code_str, Action.WARN)
        
        # 1. 재시도 한도 초과 체크 (설계안 14.2)
        if base_action == Action.RETRY and retry_count >= self.max_retries:
            # 한도 초과 시 종착 action 결정 (설계안 14.3)
            # NETWORK_ERROR 계열은 최종적으로 DROP 시켜서 크롤링 중단
            if reason_code_str in [
                ReasonCode.NETWORK_ERROR.value, 
                ReasonCode.TIMEOUT.value, 
                ReasonCode.PROXY_ERROR.value,
                ReasonCode.BOT_DETECTED.value
            ]:
                return Action.DROP
            return Action.WARN
        
        return base_action

    def is_fatal(self, action: Action) -> bool:
        """파이프라인 실행을 중단해야 하는 Fatal 에러인지 판단"""
        return action == Action.CRITICAL

# 전역 Resolver 인스턴스
def create_policy_resolver() -> PolicyResolver:
    return PolicyResolver()
