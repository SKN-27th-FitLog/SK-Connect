import pandas as pd
import math
import re
from typing import Dict, Tuple, Final, Any, Optional
from ..core.file_manager import logger
from ..core.code_manager.resolver import CodeResolver

class BaseProcessor:
    """
    데이터 정제 및 변환의 공통 기능을 제공합니다.
    (v4.0: CodeResolver 주입 및 사용)
    """
    INT_MAX: Final[int] = 2_147_483_647
    INT_MIN: Final[int] = -2_147_483_648

    def __init__(self, code_resolver: Optional[CodeResolver] = None):
        self.resolver = code_resolver

    @staticmethod
    def safe_int(value: object, default: int = 0) -> int:
        try:
            if value is None or (isinstance(value, float) and math.isnan(value)):
                return default
            s_val = str(value).replace(',', '')
            s_val = re.sub(r'[^\d-]', '', s_val)
            if not s_val: return default
            converted = int(float(s_val))
            return max(BaseProcessor.INT_MIN, min(BaseProcessor.INT_MAX, converted))
        except (ValueError, TypeError):
            return default

    @staticmethod
    def safe_float(value: object, default: float = 0.0) -> float:
        try:
            if value is None or (isinstance(value, float) and math.isnan(value)):
                return default
            s_val = str(value).replace(',', '')
            return float(s_val)
        except (ValueError, TypeError):
            return default
