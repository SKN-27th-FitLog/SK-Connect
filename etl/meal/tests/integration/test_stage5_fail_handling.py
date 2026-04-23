import pytest
from unittest.mock import MagicMock
from src.pipeline.fail_classification import FailClassification
from src.core.db_client import DBClient

@pytest.fixture
def mock_db():
    db = MagicMock(spec=DBClient)
    return db

def test_fail_classification_retry_policy(mock_db):
    # 1. 초기화
    classifier = FailClassification(db_client=mock_db)
    
    # [Case 1] 일반적인 네트워크 에러 -> RETRY 결정 확인
    ledger_1 = classifier.classify_and_log(
        stage="raw_collection",
        reason_code="NETWORK_ERROR",
        entity_id="https://test.com/fail-1",
        category_cd="CA01",
        retry_count=0
    )
    
    assert ledger_1.action == "retry"
    # DB 저장 호출 확인
    assert mock_db.execute_query.called

def test_fail_classification_drop_policy(mock_db):
    classifier = FailClassification(db_client=mock_db)
    
    # [Case 2] 입력값 오류 등 복구 불가능한 에러 -> DROP 결정 확인
    ledger_2 = classifier.classify_and_log(
        stage="target_selection",
        reason_code="INVALID_CATEGORY",
        entity_id="CA_INVALID",
        category_cd="NONE",
        retry_count=0
    )
    
    assert ledger_2.action == "drop"

def test_fail_classification_retry_limit(mock_db):
    classifier = FailClassification(db_client=mock_db)
    
    # [Case 3] 재시도 횟수 초과 (5회 이상) -> DROP으로 전환되는지 확인
    # FailResolver 코드에 따라 threshold가 다를 수 있음 (보통 5회)
    ledger_3 = classifier.classify_and_log(
        stage="raw_collection",
        reason_code="NETWORK_ERROR",
        entity_id="https://test.com/fail-limit",
        category_cd="CA01",
        retry_count=5 # 설계상 5회부터 drop
    )
    
    assert ledger_3.action == "drop"
    print(f"\n--- Stage 5 Integration Success: Correct action determined and logged.")
