from typing import Dict, Any

class FailResolver:
    """
    실패 사유(reason_code)와 시도 횟수를 기반으로 후속 조치(Action)를 결정하는 엔진입니다.
    v4 설계서의 'reason_code 정책표'를 기반으로 동작합니다.
    """
    
    def __init__(self):
        # 설계 기준 Action 매핑
        self.policy_map = {
            "NETWORK_ERROR": "retry",
            "TIMEOUT": "retry",
            "TEMPORARY_RENDER_FAIL": "retry",
            "RATE_LIMITED": "retry",
            "SELECTOR_MISMATCH": "reprocess",
            "EMPTY_EXTRACTION": "reprocess",
            "MISSING_NORMALIZED_NAME": "reprocess",
            "MISSING_NORMALIZED_ADDRESS": "reprocess",
            "INVALID_URL": "drop",
            "BLOCKED_SOURCE_POLICY": "drop",
            "NOT_RESTAURANT_ENTITY": "drop",
            "PERMANENT_SCHEMA_VIOLATION": "drop",
            "MAP_DUPLICATE_DETECTED": "drop",
            "RETRY_LIMIT_EXCEEDED": "drop"
        }

    def resolve(self, reason_code: str, retry_count: int) -> str:
        """
        Action을 결정합니다. 
        - 최대 retry 횟수(5회) 초과 시 drop으로 강제 전환합니다.
        """
        if retry_count >= 5:
            return "drop"
            
        return self.policy_map.get(reason_code, "drop")
