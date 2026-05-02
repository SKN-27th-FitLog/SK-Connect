from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime
from src.core.policy.reason_code import ReasonCode

class BaseEntityModel(BaseModel):
    """
    모든 엔티티 모델의 기본 클래스.
    설계안 13장(entity_id/ref 원칙) 준수.
    """
    entity_id: str                      # 해당 Stage/엔티티의 대표 키
    entity_ref: Dict[str, Any] = {}      # 추적용 참조 키 묶음 (target_id, store_id 등)

class StoreModel(BaseEntityModel):
    """설계안 7, 10, 13장 준수 - 매장(Shop) 모델"""
    name: str
    shop_cd: str                        # 업종 코드 (DB 코드 테이블 기준)
    address_cd: str                     # 주소 코드 (DB 코드 테이블 기준)
    address_detail: str                 # 상세 주소
    latitude: float = 0.0
    longitude: float = 0.0
    rating: float = 0.0
    canonical_url: Optional[str] = None
    source_platform: str
    source_internal_id: str
    
    # Dedup 정보 (설계안 10장)
    dedup_key: str
    dedup_key_type: str                 # canonical_url | name_address | platform_id
    dedup_rule_version: str = "v1"

class MenuModel(BaseEntityModel):
    """매장 종속 엔티티 - 메뉴"""
    store_id: Optional[str] = None
    name: str
    price: Optional[int] = None
    description: Optional[str] = None
    image_url: Optional[str] = None

class ReviewModel(BaseEntityModel):
    """매장 종속 엔티티 - 리뷰"""
    store_id: Optional[str] = None
    author: Optional[str] = None
    rating: Optional[float] = None
    content: str
    visited_at: Optional[str] = None
    source_review_id: str

class FailLedgerModel(BaseModel):
    """
    설계안 14장, 33.6 준수 - 실패 기록 모델.
    logger와 별개로 운영 기록을 담당.
    build_fail_record() 출력 구조와 일치.
    """
    batch_id: str
    run_attempt: int = 1
    stage: str
    entity_type: str
    entity_id: str
    entity_ref: Dict[str, Any] = {}
    status: str = "fail"
    reason_code: str                     # ReasonCode.value
    detail: str = ""
    retry_count: int = 0
    created_at: datetime = Field(default_factory=datetime.now)

class BatchMetricsModel(BaseModel):
    """설계안 19장 준수 - Metrics 모델"""
    batch_id: str
    category_cd: str
    stage: str
    success_count: int = 0
    fail_count: int = 0
    timestamp: datetime = Field(default_factory=datetime.now)
