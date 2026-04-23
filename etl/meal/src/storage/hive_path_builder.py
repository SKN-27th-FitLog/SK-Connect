import os
from datetime import date
from typing import Optional
from ..core.settings import settings

class HivePathBuilder:
    """
    Hive 스타일의 디렉토리 경로를 생성합니다.
    형식: crawling={stage}/service={service}/year={yyyy}/month={mm}/day={dd}/status={status}
    """
    
    def __init__(self, base_root: Optional[str] = None):
        self.base_root = base_root or settings.DATA_LAKE_ROOT

    def build(self, 
              stage: str, 
              status: str, 
              service: str = "shop", 
              dt: date = None) -> str:
        """
        계층형 경로 문자열을 반환합니다.
        """
        if dt is None:
            dt = date.today()
            
        path = os.path.join(
            self.base_root,
            f"crawling={stage}",
            f"service={service}",
            f"year={dt.year}",
            f"month={dt.month:02}",
            f"day={dt.day:02}",
            f"status={status}"
        )
        return path.replace("\\", "/") # POSIX 스타일 경로 보장

    def get_full_path(self, stage: str, status: str, file_name: str, **kwargs) -> str:
        """
        파일명을 포함한 전체 경로를 반환합니다.
        """
        dir_path = self.build(stage, status, **kwargs)
        return f"{dir_path}/{file_name}"
