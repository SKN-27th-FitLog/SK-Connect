import requests
import json
from typing import Tuple
from ..file_manager import logger

class KakaoAPI:
    """
    카카오 REST API를 이용한 위경도 변환 서비스를 제공합니다.
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://dapi.kakao.com/v2/local/search/address.json"

    def get_coordinates(self, address: str) -> Tuple[float, float]:
        """
        주소를 위경도로 변환합니다. 실패 시 (0.0, 0.0)을 반환합니다.
        """
        if not self.api_key:
            return 0.0, 0.0

        headers = {"Authorization": f"KakaoAK {self.api_key}"}
        params = {"query": address}
        
        try:
            response = requests.get(self.base_url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("documents"):
                    doc = data["documents"][0]
                    return float(doc["y"]), float(doc["x"])
            else:
                logger.error(f"!!! Kakao API Error: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"!!! Kakao API Exception: {str(e)}")
            
        return 0.0, 0.0
