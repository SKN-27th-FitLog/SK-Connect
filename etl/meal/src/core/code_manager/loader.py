import pandas as pd
from abc import ABC, abstractmethod

class CodeLoader(ABC):
    @abstractmethod
    def load(self) -> pd.DataFrame:
        pass

class CSVCodeLoader(CodeLoader):
    def __init__(self, csv_path: str):
        self.csv_path = csv_path

    def load(self) -> pd.DataFrame:
        try:
            return pd.read_csv(self.csv_path)
        except Exception as e:
            raise RuntimeError(f"Failed to load code table from {self.csv_path}: {e}")

class DBCodeLoader(CodeLoader):
    """
    데이터베이스의 'codeT' 테이블에서 코드 정보를 로드합니다.
    """
    def __init__(self, db_client):
        self.db = db_client

    def load(self) -> pd.DataFrame:
        try:
            # v4 설계 원칙: 코드 테이블은 DB에서 직접 조회한다.
            query = 'SELECT cd, name, cd_info, cd_upper FROM "codeT"'
            results = self.db.execute_query(query)
            return pd.DataFrame(results)
        except Exception as e:
            raise RuntimeError(f"Failed to load code table from database: {e}")
