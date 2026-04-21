import pandas as pd
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

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
