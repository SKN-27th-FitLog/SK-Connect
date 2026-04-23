import os
import asyncio
from typing import List, Dict, Any
from datetime import datetime
from src.pipeline.stages.base_stage import BaseStage
from src.collectors.base_collector import BaseCollector
from src.core.storage.path_builder import HivePathBuilder
from src.core.storage.jsonl_writer import JsonlWriter
from src.core.policy.exceptions import BasePipelineException
from src.core.policy.reason_code import ReasonCode

class Stage1RawCollection(BaseStage):
    """
    설계안 11, 12, 18장 준수 - Raw 데이터 수집 Stage.
    Shard 단위로 실행되며 결과를 Hive 스타일 경로에 저장.
    """
    def __init__(self, collector: BaseCollector, shard_size: int = 10):
        super().__init__("raw_collection")
        self.collector = collector
        self.shard_size = shard_size

    def _create_shards(self, targets: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """대상 목록을 Shard 단위로 분할 (설계안 12장)"""
        return [targets[i:i + self.shard_size] for i in range(0, len(targets), self.shard_size)]

    async def execute_shard(
        self, 
        shard_targets: List[Dict[str, Any]], 
        batch_id: str, 
        category_cd: str,
        shard_id: str
    ) -> List[Dict[str, Any]]:
        """
        한 Shard 내의 모든 대상을 수집.
        """
        results = []
        now = datetime.now()
        
        # 저장 경로 생성 (상태별로 분리되나, 여기서는 일괄 수집 후 결과에 따라 경로 결정 가능)
        # 설계안 18.1: status=success/fail 경로 반영
        
        for target in shard_targets:
            target_id = target.get('target_id')
            url = target.get('url')
            
            try:
                # 1. 수집 수행
                raw_data = await self.collector.collect(url)
                
                # 2. 결과 저장 (HTML 파일)
                success_path = HivePathBuilder.build_path(
                    process="raw", service="shop", category_cd=category_cd,
                    stage=self.stage_name, batch_id=batch_id, status="success", dt=now
                )
                filename = HivePathBuilder.build_filename(extension="html", dt=now)
                
                os.makedirs(success_path, exist_ok=True)
                full_file_path = os.path.join(success_path, filename)
                
                with open(full_file_path, "w", encoding="utf-8") as f:
                    f.write(raw_data["raw_content"])
                
                # 3. 메타데이터 기록
                results.append({
                    "entity_id": target_id,
                    "entity_ref": {"target_id": target_id, "url": url, "shard_id": shard_id},
                    "raw_file_path": full_file_path,
                    "status": "success",
                    "collected_at": now.isoformat()
                })
                
            except BasePipelineException as e:
                # 파이프라인 예외 발생 시 기록
                self.logger.warning(f"Failed to collect {url}: {e.reason_code.name}")
                results.append({
                    "entity_id": target_id,
                    "entity_ref": {"target_id": target_id, "url": url, "shard_id": shard_id},
                    "status": "fail",
                    "reason_code": e.reason_code.name,
                    "detail": e.detail,
                    "collected_at": now.isoformat()
                })
            except Exception as e:
                self.logger.error(f"Unexpected error collecting {url}: {str(e)}")
                results.append({
                    "entity_id": target_id,
                    "entity_ref": {"target_id": target_id, "url": url, "shard_id": shard_id},
                    "status": "fail",
                    "reason_code": ReasonCode.UNKNOWN_ERROR.name,
                    "detail": str(e),
                    "collected_at": now.isoformat()
                })
        
        # 4. Shard 결과 메타데이터 (JSONL) 저장
        metadata_path = HivePathBuilder.build_path(
            process="raw", service="shop", category_cd=category_cd,
            stage=self.stage_name, batch_id=batch_id, status="metadata", dt=now
        )
        metadata_filename = f"shard_{shard_id}_{HivePathBuilder.build_filename(extension='jsonl', dt=now)}"
        JsonlWriter.write(metadata_path, metadata_filename, results)
        
        return results

    async def execute(self, targets: List[Dict[str, Any]], batch_id: str, category_cd: str) -> List[Dict[str, Any]]:
        """전체 대상 수집 실행 (Shard 기반)"""
        shards = self._create_shards(targets)
        all_results = []
        
        for i, shard in enumerate(shards):
            shard_id = f"{i:03d}"
            shard_result = await self.execute_shard(shard, batch_id, category_cd, shard_id)
            all_results.extend(shard_result)
            
        return all_results
