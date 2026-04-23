from typing import List, Dict, Any
from src.pipeline.stages.base_stage import BaseStage
from src.services.parsers.base_parser import BaseParser
from src.core.storage.path_builder import HivePathBuilder
from src.core.storage.jsonl_writer import JsonlWriter
from datetime import datetime
import os

class Stage2CandidateParsing(BaseStage):
    """
    설계안 2.2 준수 - Candidate Parsing Stage.
    Raw HTML을 읽어 구조화된 Candidate JSONL을 생성.
    """
    def __init__(self, parser: BaseParser):
        super().__init__("candidate_parsing")
        self.parser = parser

    def execute(self, raw_metadata: List[Dict[str, Any]], batch_id: str, category_cd: str) -> List[Dict[str, Any]]:
        """
        수집된 Raw 파일들을 순회하며 파싱 수행.
        """
        candidates = []
        now = datetime.now()
        
        for record in raw_metadata:
            if record.get("status") != "success":
                continue
                
            file_path = record.get("raw_file_path")
            if not file_path or not os.path.exists(file_path):
                continue
                
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    html = f.read()
                
                # 1. 파싱 수행
                shop_data = self.parser.parse_shop(html)
                menus = self.parser.parse_menus(html)
                reviews = self.parser.parse_reviews(html)
                
                # 2. Candidate 데이터 구성 (설계안 13장 참조)
                candidate = {
                    "entity_id": record.get("entity_id"),
                    "entity_ref": record.get("entity_ref", {}),
                    "shop": shop_data,
                    "menus": menus,
                    "reviews": reviews,
                    "parsed_at": now.isoformat()
                }
                candidates.append(candidate)
                
            except Exception as e:
                self.logger.error(f"Failed to parse {file_path}: {str(e)}")
                # 실패 기록은 필요 시 별도 Stage 5에서 처리하도록 결과에 포함 가능
        
        # 3. Candidate 결과 저장 (JSONL)
        candidate_path = HivePathBuilder.build_path(
            process="candidate", service="shop", category_cd=category_cd,
            stage=self.stage_name, batch_id=batch_id, status="success", dt=now
        )
        filename = HivePathBuilder.build_filename(extension="jsonl", dt=now)
        JsonlWriter.write(candidate_path, filename, candidates)
        
        self.logger.info(f"Parsed {len(candidates)} candidates for batch {batch_id}")
        return candidates
