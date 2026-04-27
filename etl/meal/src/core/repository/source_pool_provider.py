import logging
import csv
import os
from typing import List, Dict, Any

logger = logging.getLogger("core.repository")

class SourcePoolProvider:
    """
    [설계안 6.1 준수] - 수집 후보 Pool 제공자.
    target.csv 외에 수집 대상을 확장할 수 있는 인터페이스 제공.
    """
    def __init__(self, seed_file: str = "target.csv"):
        self.seed_file = seed_file

    def get_candidates(self, category_cd: str) -> List[Dict[str, Any]]:
        """
        [설계안 215, 216 준수] - 1차 seed(target.csv) 및 확장 후보 확보.
        """
        candidates = []
        if not os.path.exists(self.seed_file):
            logger.warning(f"Seed file {self.seed_file} not found.")
            return []

        # 현재는 target.csv를 기반으로 동작하지만, 
        # 향후 별도 DB나 API를 통해 pool을 확장하도록 설계됨.
        with open(self.seed_file, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('category_cd') == category_cd:
                    candidates.append({
                        "address_cd": row.get('address_cd'),
                        "category_cd": category_cd,
                        "raw_info": row
                    })
        
        return candidates

source_pool_provider = SourcePoolProvider()
