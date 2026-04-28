# 핫픽스 수정 대상 코드 (Diff Review)

앞서 설명해 드린 **Failcheck 로직 버그** 및 **CrawlService Shard 인터페이스 누락** 문제를 해결하기 위한 구체적인 코드 변경 사항입니다.

---

### 1. `src/projects/failcheck/failcheck_service.py`
정책(Policy) 중앙 통제화에 맞춰 `PolicyResolver`를 사용하도록 수정하고, 치명적인 오타 및 구형 규격을 바로잡습니다.

```diff
--- src/projects/failcheck/failcheck_service.py
+++ src/projects/failcheck/failcheck_service.py
@@ -4,8 +4,8 @@
 from datetime import datetime
 from src.core.storage.path_builder import HivePathBuilder
 from src.core.storage.jsonl_writer import JsonlWriter
-from src.core.resolver import Resolver
+from src.core.policy.resolver import policy_resolver, Action
 from src.core.dispatch import Dispatcher
 
 logger = logging.getLogger("failcheck_project")
@@ -19,7 +19,7 @@
         """
         logger.info(f"--- Starting FAILCHECK Project: {category_cd} ---")
         dt = datetime.now()
-        date_str = dt.strftime('%Y%n%d') # Design Policy: 동일 날짜 반복 재시도 방지용 스트링
+        date_str = dt.strftime('%Y%m%d') # Design Policy: 동일 날짜 반복 재시도 방지용 스트링
         
         # 1. 모든 스테이지의 실패(status=fail) 파일 수집
         fail_files = []
@@ -60,11 +60,12 @@
             else:
                 # Policy 2: Resolver에 판단 위임
-                reason_code = record.get("reason_code")
-                action = Resolver.decide_action(reason_code, record)
+                reason_code = record.get("reason_code", "UNKNOWN_ERROR")
+                stage = record.get("stage", "unknown")
+                action = policy_resolver.resolve(reason_code, stage, retry_count).name
             
             # 메타데이터 업데이트 (재시도 날짜 기록 또는 폐기 기록)
-            if action in ("RETRY_CRAWL", "REPROCESS", "RETRY_SAVE"):
+            if action in ("RETRY", "REPROCESS"):
                 record["last_retry_date"] = date_str
             elif action == "DROP":
                 record["final_action"] = "DROP"
```

---

### 2. `src/projects/crawl/crawl_service.py`
`Stage1RawCollection` 내부에서 임의로 분할하던 방식(1건으로 고정) 대신, `BatchUtil`을 활용해 서비스 레벨에서 Shard를 분할`split_targets_into_shards`하고 개별 `execute_shard`를 지원하는 인터페이스로 변경합니다. (추후 외부 Lambda/SQS 연동 대비)

```diff
--- src/projects/crawl/crawl_service.py
+++ src/projects/crawl/crawl_service.py
@@ -29,14 +29,29 @@
 
         # 3. Stage 1: 원본 데이터 수집 실행
         collector = get_collector(platform)
-        stage1 = get_stage(STAGE_RAW_COLLECTION, collector=collector, shard_size=1)
+        # 내부 Sharding 대신 Service에서 Sharding 관리 인터페이스 제공
+        stage1 = get_stage(STAGE_RAW_COLLECTION, collector=collector)
         
-        # Design Policy: run_attempt를 명시적으로 전달하여 실행 이력 추적성 강화
-        await stage1.execute(targets, batch_id, category_cd, run_attempt=run_attempt)
+        shard_size = 10 # 기본 Shard 크기
+        shards = BatchUtil.split_targets_into_shards(targets, shard_size)
+        
+        for i, shard_targets in enumerate(shards):
+            shard_id = BatchUtil.generate_shard_id(batch_id, i)
+            logger.info(f"Executing Shard {shard_id} ({len(shard_targets)} targets)")
+            
+            # 실제 AWS 환경에서는 이 부분부터 별도의 Lambda/SQS 로 분리될 수 있음.
+            # 현재는 local 루프 실행으로 시뮬레이션
+            await stage1.execute_shard(
+                shard_targets=shard_targets, 
+                batch_id=batch_id, 
+                category_cd=category_cd, 
+                shard_id=shard_id, 
+                run_attempt=run_attempt
+            )
         
         logger.info(f"--- CRAWL Project Finished ---")
         return {
             "batch_id": batch_id,
             "targets_processed": len(targets),
+            "shards_created": len(shards),
             "run_attempt": run_attempt
         }
```
