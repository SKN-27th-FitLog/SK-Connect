import pandas as pd
import math
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
        try:
            if value is None or (isinstance(value, float) and math.isnan(value)):
                return default
            converted = int(float(str(value)))
            return max(BaseProcessor.INT_MIN, min(BaseProcessor.INT_MAX, converted))
        except (ValueError, TypeError):
            return default

    @staticmethod
    def safe_float(value: object, default: float = 0.0) -> float:
        try:
            if value is None or (isinstance(value, float) and math.isnan(value)):
                return default
            return float(str(value))
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
            # LA00 하위 지역 코드 매핑
            address_map = {
                str(row["name"]).strip(): str(row["cd"]).strip()
                for _, row in df_cd.iterrows()
                if str(row.get("cd_upper", "")).strip() == "LA00"
            }
            return category_map, address_map
        except Exception as e:
            logger.error(f"!!! 코드 테이블 로드 실패: {e}")
            return {}, {}
