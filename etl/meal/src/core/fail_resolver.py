from typing import Dict, Any
from .constants.reason_codes import ReasonCode, FailAction

class FailResolver:
    """
    실패 사유(ReasonCode)와 시도 횟수를 기반으로 후속 조치(FailAction)를 결정하는 엔진입니다.
    """
    
    def __init__(self):
        # Enum에 정의된 기본 액션을 매핑
        self.policy_map = {rc.name: rc.default_action.value for rc in ReasonCode}

    def resolve(self, reason_code_name: str, retry_count: int) -> str:
        """
        Action을 결정합니다. 
        - 최대 retry 횟수(5회) 초과 시 DROP으로 강제 전환합니다.
        """
        if retry_count >= 5:
            return FailAction.DROP.value
            
        return self.policy_map.get(reason_code_name, FailAction.ALERT_ONLY.value)
