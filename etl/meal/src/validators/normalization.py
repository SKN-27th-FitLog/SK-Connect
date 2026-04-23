import re
from typing import Optional

def normalize_name(name: str) -> str:
    """
    상호명 정규화: 특수문자 제거, 연속된 공백 제거, 소문자화
    """
    if not name:
        return ""
    # 1. 특수문자 제거 (한글, 영문, 숫자만 남김)
    name = re.sub(r'[^가-힣a-zA-Z0-9\s]', '', name)
    # 2. 연속 공백 하나로 축소 및 양끝 공백 제거
    name = re.sub(r'\s+', ' ', name).strip()
    return name.lower()

def normalize_address(address: str) -> str:
    """
    주소 정규화: 지번/도로명 주소 가공 (기본 트리밍 및 연속 공백 정리)
    """
    if not address:
        return ""
    # 연속 공백 정리
    address = re.sub(r'\s+', ' ', address).strip()
    return address
