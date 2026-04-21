import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from ..constants.schema_constants import SCHEMA_CONTRACT

class SchemaValidator:
    """
    DB 제약사항 중심의 스키마 계약을 기반으로 데이터 무결성을 검증합니다.
    (v4.0: Strict Null check, Validation > Default priority)
    """

    # Null 계열 정의 ("", " ", None, NaN)
    NULL_VALUES = ["", " ", None]

    @classmethod
    def is_null(cls, value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, float) and np.isnan(value):
            return True
        if isinstance(value, str) and value.strip() == "":
            return True
        return False

    def validate(self, table_name: str, data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        테이블별 스키마 계약에 따라 데이터를 검증합니다.
        """
        contract = SCHEMA_CONTRACT.get(table_name)
        if not contract:
            return True, None # 계약이 없는 테이블은 통과

        cols = contract["columns"]
        required_cols = contract["required"]
        defaults = contract["defaults"]

        # 1. 필수 컬럼(Not-null) 검증
        # 정책: Default가 있더라도 필수 컬럼 값이 누락되면 무조건 Fail 처리
        for req_col in required_cols:
            val = data.get(req_col.value)
            if self.is_null(val):
                return False, f"Required column missing: {req_col.value}"

        # 2. 값 보정 (Default 적용 - 비즈니스 의미가 없는 운영용 컬럼만)
        for col_enum, default_val in defaults.items():
            col_name = col_enum.value
            if self.is_null(data.get(col_name)):
                data[col_name] = default_val

        return True, None
