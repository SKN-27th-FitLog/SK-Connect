import json
import os
from typing import List, Dict, Any, Union
from pydantic import BaseModel
from datetime import datetime

class JsonlWriter:
    """
    설계안 4장 및 18.3 준수 - JSONL 파일 기록 유틸리티.
    overwrite 금지 원칙을 지키며 데이터를 추가하거나 새 파일을 생성.
    """
    
    @staticmethod
    def write(path: str, filename: str, data: List[Union[Dict[str, Any], BaseModel]]):
        """
        데이터를 JSONL 형식으로 기록.
        폴더가 없으면 생성.
        """
        if not data:
            return

        os.makedirs(path, exist_ok=True)
        file_path = os.path.join(path, filename)
        
        # 설계안 18.3: overwrite 금지. 
        # 만약 파일이 이미 존재하면 (드문 경우지만) timestamp를 더 정교하게 하거나 에러를 낸다.
        # 여기서는 신규 파일 생성 원칙을 위해 'a' (append) 또는 중복 체크 수행.
        # 설계안 18.2의 timestamp 파일명 규격상 중복 가능성이 낮으나 안전하게 처리.
        
        mode = 'a' if os.path.exists(file_path) else 'w'
        
        with open(file_path, mode, encoding='utf-8') as f:
            for item in data:
                # Pydantic 모델인 경우 dict로 변환
                if isinstance(item, BaseModel):
                    record = item.model_dump(mode='json')
                else:
                    record = item
                
                # datetime 객체 직렬화 지원 (이미 json 모드로 변환되지 않은 경우 대비)
                f.write(json.dumps(record, ensure_ascii=False, default=str) + '\n')

    @staticmethod
    def read(file_path: str) -> List[Dict[str, Any]]:
        """JSONL 파일 읽기"""
        results = []
        if not os.path.exists(file_path):
            return results
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    results.append(json.loads(line))
        return results
