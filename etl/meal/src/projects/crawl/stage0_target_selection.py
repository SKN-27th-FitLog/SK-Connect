import os
import csv
from typing import List, Dict, Any
import logging

from src.core.base_stage import BaseStage
from src.core.repository.code_table_repository import CodeTableRepository, code_repo

class Stage0TargetSelection(BaseStage):
    """
    [요구사항 6.2 일치] - Daily Target Selection.
    원칙: target.csv에서 주소/카테고리 코드를 읽어 수집 시드 생성.
    """
    NAME = "target_selection"

    def __init__(self, seed_file: str = "target.csv", code_repository: CodeTableRepository = code_repo):
        super().__init__(self.NAME)
        self.seed_file = seed_file
        self.code_repo = code_repository

    def execute(self, category_cd: str, platform: str = "DiningCode") -> List[Dict[str, Any]]:
        self.code_repo.preload()
        selected_seeds = []

        if not os.path.exists(self.seed_file):
            self.logger.warning(f"Seed file {self.seed_file} not found.")
            return []

        with open(self.seed_file, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                addr_cd = row.get('address_cd')
                if row.get('category_cd') != category_cd:
                    continue
                
                addr_info = self.code_repo.get_address_info(addr_cd)
                shop_info_name = self.code_repo.get_shop_code_name(category_cd)
                
                if addr_info and shop_info_name:
                    selected_seeds.append({
                        "address_cd": addr_cd,
                        "category_cd": category_cd,
                        "address_name": addr_info['name'],
                        "category_name": shop_info_name,
                        "source_platform": platform,
                        "search_query": f"{addr_info['name']} {shop_info_name}"
                    })

        self.logger.info(f"Selected {len(selected_seeds)} search seeds for {platform}/{category_cd}")
        return selected_seeds
