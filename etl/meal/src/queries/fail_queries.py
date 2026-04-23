"""
실패 내역(Fail Ledger) 관련 SQL 상수를 정의합니다.
"""

INSERT_FAIL_LEDGER = """
INSERT INTO fail_ledger (
    entity_id, category_cd, batch_id, stage, 
    reason_code, reason_detail, action, status, 
    retry_count, last_attempt_at
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (entity_id, category_cd) 
DO UPDATE SET 
    stage = EXCLUDED.stage,
    reason_code = EXCLUDED.reason_code,
    reason_detail = EXCLUDED.reason_detail,
    action = EXCLUDED.action,
    status = EXCLUDED.status,
    retry_count = fail_ledger.retry_count + 1,
    last_attempt_at = EXCLUDED.last_attempt_at
"""
