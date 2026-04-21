import pandas as pd
from typing import Optional, List, Dict, Any
from .loader import CodeLoader
from ..constants.code_rules import CodePrefix, LookupPolicy

class CodeResolver:
    """
    정의된 정책에 따라 코드 테이블에서 정확한 매핑 코드를 찾아내는 역할을 수행합니다.
    (v4.0: Exact Match Only, Strict Prefix support)
    """
    
    def __init__(self, loader: CodeLoader):
        self._df = loader.load()
        # 공백 제거 및 인덱싱 처리
        self._df['cd'] = self._df['cd'].astype(str).str.strip()
        self._df['name'] = self._df['name'].astype(str).str.strip()
        self._df['cd_info'] = self._df['cd_info'].astype(str).str.strip()

    def resolve(self, name: str, prefix: CodePrefix, on_fail: LookupPolicy = LookupPolicy.FALLBACK_NONE) -> Optional[str]:
        """
        명칭(name)을 기반으로 특정 프리픽스(prefix)를 가진 코드를 조회합니다.
        """
        if not name or name.lower() in ['none', 'nan', '']:
            return self._handle_fail(f"Empty search name for prefix {prefix.value}", on_fail)
            
        # 1. Exact Match (name 컬럼 또는 cd_info 컬럼에서 검색)
        mask = (
            ((self._df['name'] == name) | (self._df['cd_info'].str.contains(name, na=False))) &
            (self._df['cd'].str.startswith(prefix.value))
        )
        
        matches = self._df[mask]
        
        if matches.empty:
            return self._handle_fail(f"No code found for '{name}' with prefix {prefix.value}", on_fail)
            
        # 2. 중복 매칭 시 첫 번째 항목 선택 (현재 정책)
        code = matches.iloc[0]['cd']
        return code

    def get_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        """코드로 직접 정보 조회"""
        match = self._df[self._df['cd'] == code]
        if match.empty:
            return None
        return match.iloc[0].to_dict()

    def _handle_fail(self, message: str, policy: LookupPolicy) -> Optional[str]:
        if policy == LookupPolicy.RAISE:
            raise ValueError(f"Code Resolver Error: {message}")
        return None
