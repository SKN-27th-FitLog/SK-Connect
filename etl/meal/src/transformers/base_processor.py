import pandas as pd
import math
import re
from typing import Dict, Tuple, Final
from ..core.file_manager import logger

class BaseProcessor:
    """
    데이터 정제 및 변환의 공통 기능을 제공합니다.
    """
    INT_MAX: Final[int] = 2_147_483_647
    INT_MIN: Final[int] = -2_147_483_648

    @staticmethod
    def safe_int(value: object, default: int = 0) -> int:
        """
        문자열 형식의 가격(예: '4,500원', '₩10,000')을 정수로 안전하게 변환합니다.
        """
        try:
            if value is None or (isinstance(value, float) and math.isnan(value)):
                return default
            
            # 1. 문자열로 변환 후 숫자와 마이너스 부호 외의 모든 문자 제거
            s_val = str(value).replace(',', '') # 콤마 우선 제거
            s_val = re.sub(r'[^\d-]', '', s_val) # 숫자와 - 제외 제거 (원, ₩ 등)
            
            if not s_val:
                return default
                
            converted = int(float(s_val))
            return max(BaseProcessor.INT_MIN, min(BaseProcessor.INT_MAX, converted))
        except (ValueError, TypeError):
            return default

    @staticmethod
    def safe_float(value: object, default: float = 0.0) -> float:
        try:
            if value is None or (isinstance(value, float) and math.isnan(value)):
                return default
            # float 변환 전 콤마 제거
            s_val = str(value).replace(',', '')
            return float(s_val)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def load_code_tables(code_csv: str) -> Tuple[Dict[str, str], Dict[str, str]]:
        try:
            df_cd = pd.read_csv(code_csv)
            category_map = {
                str(row["name"]).strip(): str(row["cd"]).strip()
                for _, row in df_cd.iterrows()
                if str(row["cd"]).strip().startswith(("FC", "CA"))
            }
            address_map = {
                str(row["name"]).strip(): str(row["cd"]).strip()
                for _, row in df_cd.iterrows()
                if str(row.get("cd_upper", "")).strip() == "LA00"
            }
            return category_map, address_map
        except Exception as e:
            logger.error(f"!!! 코드 테이블 로드 실패: {e}")
            return {}, {}
