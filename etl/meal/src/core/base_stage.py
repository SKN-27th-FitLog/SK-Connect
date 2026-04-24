from abc import ABC, abstractmethod
from typing import Any, Dict, List
import logging

class BaseStage(ABC):
    """
    설계안 3.1 준수 - 파이프라인 Stage 기본 클래스.
    Stage는 데이터 처리만 담당하며 정책 판단은 하지 않음.
    """
    def __init__(self, stage_name: str):
        self.stage_name = stage_name
        self.logger = logging.getLogger(f"stage.{stage_name}")

    @abstractmethod
    def execute(self, input_data: Any) -> Any:
        """Stage 실행 로직 구현부"""
        pass
