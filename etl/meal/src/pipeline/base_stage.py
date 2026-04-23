from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from ..core.file_manager import logger
from ..core.utils.decorators import trace_stage

class BaseStage(ABC):
    """
    모든 파이프라인 단계(Stage)의 추상 베이스 클래스입니다.
    표준화된 실행 인터페이스와 로깅을 제공합니다.
    """
    
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def _execute(self, input_data: Any) -> Any:
        """
        실제 비즈니스 로직을 구현하는 내부 메서드입니다.
        """
        pass

    def run(self, input_data: Any) -> Any:
        """
        단계를 실행하고 시간을 측정하며 로깅합니다.
        trace_stage 데코레이터와 유사한 역할을 수행하거나 직접 사용할 수 있습니다.
        """
        # trace_stage를 직접 클래스 내 메서드에 적용하기 어려우므로 수동 로깅 또는 
        # 데코레이팅된 헬퍼를 호출할 수 있습니다.
        return self._execute(input_data)
