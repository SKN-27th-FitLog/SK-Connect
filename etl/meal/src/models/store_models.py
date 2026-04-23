from pydantic import BaseModel, Field
from typing import List, Optional

class MenuCandidate(BaseModel):
    name: str
    price: Optional[int] = None
    description: Optional[str] = None
    rating: Optional[float] = None

class ReviewCandidate(BaseModel):
    content: str
    rating: Optional[float] = None
    author_id: Optional[str] = None

class StoreCandidate(BaseModel):
    """파싱된 가게 데이터 모델"""
    source_platform: str
    source_internal_id: str
    name: str
    address: Optional[str] = None
    canonical_url: str
    category_cd: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    rating: Optional[float] = None
    
    menus: List[MenuCandidate] = Field(default_factory=list)
    reviews: List[ReviewCandidate] = Field(default_factory=list)

class NormalizedStore(StoreCandidate):
    """정규화 및 검증이 완료된 가게 데이터 모델"""
    normalized_name: str
    normalized_address: str
    dedup_key: str
    dedup_rule_version: str = "v1"
    
    # 데이터 완성도 지표 (0.0 ~ 1.0)
    entity_completeness: float = 1.0
