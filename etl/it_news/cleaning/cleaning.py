"""
"""

# 패키지
import pandas as pd
from datetime import datetime

# 모듈
from common.postgresql.connection import PostgreDB




##############################################
# DB에서 성공한 날짜 확인 후 리턴 
##############################################

def get_success_date() -> datetime:
    """DB에서 성공한 날짜 확인 후 리턴"""
    conn = PostgreDB()
    max_rows = conn.run_query("SELECT MAX(created_at) FROM crawling")
    raw = max_rows[0][0] if max_rows else None
    return raw



##############################################
# 수집 성공데이터 전체 확인해서 하나의 데이터 프레임으로 
##############################################