import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta

from src.core.base_stage import BaseStage
from src.core.storage.path_builder import HivePathBuilder
from src.core.storage.jsonl_writer import JsonlWriter
from src.core.policy.resolver import PolicyResolver, policy_resolver, Action

class Stage5FailClassification(BaseStage):
    """
    [설계안 19 일치] - Fail Classification Stage.
    실패 사유를 분류하고 액션(재처리, 폐기 등)을 결정하여 핸들러가 반환값을 통해 
    Target Project 배분 폴더(dispatch JSONL)로 기록할 수 있게 합니다.
    """
    NAME = "fail_classification"

    def __init__(self, resolver: PolicyResolver = policy_resolver):
        super().__init__(self.NAME)
        self.policy_resolver = resolver

    def execute(self, shard_results: List[Dict[str, Any]], batch_id: str, category_cd: str, origin_stage: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        shard_results: 원본 프로젝트(crawl, process, save)에서 실패한 레코드 집합
        반환값: 액션별로 분류된 딕셔너리 (각 타겟 프로젝트 핸들러가 주워가기 위함)
        """
        now = datetime.now()
        
        # Action별 분배 버킷
        dispatched_buckets = {
            "fail_ledger": [], # 항상 전체 기록 (관측용)
            "retry": [],
            "reprocess": [],
            "drop": [],
            "warn": []
        }

        for res in shard_results:
            reason_code_str = res.get("reason_code", "UNKNOWN_ERROR")
            
            # 메타데이터 추출 및 누적
            current_retry_count = res.get("retry_count", 0) + 1 # 실패가 발생했으니 1 증가
            
            # Action 판별
            action = self.policy_resolver.resolve(
                reason_code_str=reason_code_str,
                stage=origin_stage,
                retry_count=current_retry_count
            )
            
            # 실패 당일 + 1일 (같은 날 retry 금지 정책)
            retry_available_date = now + timedelta(days=1)
            
            failure_entry = {
                "entity_id": res.get("entity_id"),
                "entity_type": res.get("entity_type"),
                "reason_code": reason_code_str,
                "detail": res.get("detail", ""),
                "failed_at": now.isoformat(),
                "action_taken": action.name,
                
                # 원본 메타데이터 필수 보존
                "metadata": {
                    "origin_batch_id": batch_id,
                    "origin_stage": origin_stage,
                    "retry_count": current_retry_count,
                    "retry_available_date": retry_available_date.strftime("%Y-%m-%d") if action == Action.RETRY else None,
                    "entity_ref": res.get("entity_ref", {})
                },
                
                # Payload 보존 (다음 재시도 시 사용될 원본 데이터)
                "data": res.get("data", {})
            }
            
            # 1. 공통 Ledger에는 우선 모두 기록
            dispatched_buckets["fail_ledger"].append(failure_entry)
            
            # 2. Action에 따른 라우팅
            if action == Action.RETRY:
                dispatched_buckets["retry"].append(failure_entry)
            elif action == Action.REPROCESS:
                dispatched_buckets["reprocess"].append(failure_entry)
            elif action == Action.DROP:
                dispatched_buckets["drop"].append(failure_entry)
            else:
                dispatched_buckets["warn"].append(failure_entry)

        self.logger.info(
            f"Classified {len(shard_results)} failures from stage '{origin_stage}' -> "
            f"Retry: {len(dispatched_buckets['retry'])}, "
            f"Reprocess: {len(dispatched_buckets['reprocess'])}, "
            f"Drop: {len(dispatched_buckets['drop'])}."
        )

        return dispatched_buckets
