import pytest
import pandas as pd
import os
from src.core.code_manager.loader import CSVCodeLoader
from src.core.code_manager.resolver import CodeResolver
from src.core.constants.code_rules import CodePrefix, LookupPolicy
from src.core.schema.validator import SchemaValidator
from src.core.constants.schema_constants import MapsColumns

@pytest.fixture
def mock_code_csv(tmp_path):
    d = tmp_path / "subdir"
    d.mkdir()
    p = d / "codeT.csv"
    p.write_text("cd,name,cd_info,cd_upper\nCA01,맛집,식당,CA00\nFC01,한식,KOREAN,FC00\nLA01,서울,SEOUL,LA00", encoding="utf-8")
    return str(p)

def test_code_resolver(mock_code_csv):
    loader = CSVCodeLoader(mock_code_csv)
    resolver = CodeResolver(loader)
    
    # 1. Exact Match 성공
    assert resolver.resolve("맛집", CodePrefix.CATEGORY) == "CA01"
    assert resolver.resolve("한식", CodePrefix.FOOD) == "FC01"
    
    # 2. cd_info 검색 성공
    assert resolver.resolve("KOREAN", CodePrefix.FOOD) == "FC01"
    
    # 3. 실패 시 정책 (None 반환)
    assert resolver.resolve("일식", CodePrefix.FOOD) is None

def test_schema_validator():
    validator = SchemaValidator()
    
    # 1. 필수값 누락 (Fail)
    data = {MapsColumns.NAME.value: "테스트 식당"} # ADDRESS_DETAIL 누락
    is_valid, error = validator.validate("maps", data)
    assert is_valid is False
    assert "Required column missing" in error
    
    # 2. Null 계열 처리 (Fail)
    data = {
        MapsColumns.NAME.value: " ", 
        MapsColumns.ADDRESS_DETAIL.value: "서울",
        MapsColumns.LATITUDE.value: 37.5,
        MapsColumns.LONGITUDE.value: 127.0
    }
    is_valid, _ = validator.validate("maps", data)
    assert is_valid is False # " " 은 Null로 간주
    
    # 3. 정상 데이터 및 Default 적용
    data = {
        MapsColumns.NAME.value: "정상 식당",
        MapsColumns.ADDRESS_DETAIL.value: "서울 강남구",
        MapsColumns.LATITUDE.value: 37.5,
        MapsColumns.LONGITUDE.value: 127.0,
        "food_category_cd": "FC01" # Shop용 데이터 믹스 가정
    }
    # Shop 테이블용 검증 (Rating은 default 0.0 적용되어야 함)
    # 실제 시스템에서는 loader가 테이블별로 호출함
    shop_data = {
        "map_id": 1,
        "category_cd": "FC01"
    }
    is_valid, _ = validator.validate("shop", shop_data)
    assert is_valid is True
    assert shop_data["rating"] == 0.0 # Default 적용됨
