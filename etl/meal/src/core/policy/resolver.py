from enum import Enum, auto
from typing import Dict, Any, Optional
from src.core.policy.reason_code import ReasonCode

class Action(Enum):
    """설계안 14.3 준수 - 실패에 대한 후속 조치 정의"""
    RETRY = auto()      # 다음 배치에 포함하여 재시도
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
        self._rules: Dict[ReasonCode, Action] = {
            ReasonCode.NETWORK_ERROR: Action.RETRY,
            ReasonCode.TIMEOUT: Action.RETRY,
            ReasonCode.PROXY_ERROR: Action.RETRY,
            
            ReasonCode.SELECTOR_MISMATCH: Action.REPROCESS,
            ReasonCode.BOT_DETECTED: Action.RETRY,
            
            ReasonCode.INVALID_URL: Action.DROP,
            ReasonCode.NOT_RESTAURANT_ENTITY: Action.DROP,
            ReasonCode.NOT_FOUND: Action.DROP,
            
            ReasonCode.CONFLICTING_DEDUP_SIGNALS: Action.WARN,
            ReasonCode.UNDEFINED_CODE_DETECTED: Action.REPROCESS, # 설계안 16. reprocess 승격 후보
            
            ReasonCode.DB_CONSTRAINT_VIOLATION: Action.WARN,
            ReasonCode.INVALID_DATA_FORMAT: Action.WARN,
        }

    def resolve(
        self, 
        reason_code: ReasonCode, 
        stage: str, 
        retry_count: int = 0
    ) -> Action:
        """
        최종 action 결정 로직.
        설계안 14.2, 14.3 반영.
        """
        base_action = self._rules.get(reason_code, Action.WARN)
        
        # 1. 재시도 한도 초과 체크 (설계안 14.2)
        if base_action == Action.RETRY and retry_count >= self.max_retries:
            # 한도 초과 시 종착 action 결정 (설계안 14.3)
            if reason_code in [ReasonCode.NETWORK_ERROR, ReasonCode.TIMEOUT]:
                return Action.DROP
            return Action.WARN
        
        # 2. Stage별 특수 규칙 (필요 시 추가)
        # 예: Stage 4(Load)에서 발생한 특정 에러는 무조건 REPROCESS 등
        
        return base_action

    def is_fatal(self, action: Action) -> bool:
        """파이프라인 실행을 중단해야 하는 Fatal 에러인지 판단"""
        return action == Action.CRITICAL

# 전역 Resolver 인스턴스
policy_resolver = PolicyResolver()
