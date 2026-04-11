import os
import sys
import re
import shutil
import requests
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from datetime import datetime

import pandas as pd

# members 임포트 지원
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.append(str(Path(__file__).resolve().parent))

try:
    from members import Status
except ImportError:
    class Status: ACTIVE = "ST01"

def normalize_string(text: str) -> str:
    """공백 및 특수문자를 제거하고 소문자로 통일하여 정규화합니다."""
    if not text:
        return ""
    # 한글, 영문, 숫자만 남기고 제거
    text = re.sub(r'[^가-힣a-zA-Z0-9]', '', text)
    return text.lower()

def safe_re_sub_space(text: str) -> str:
    """모든 종류의 공백을 제거합니다 (맵핑용)."""
    if not text:
        return ""
    return re.sub(r'\s+', '', str(text))

def generate_content_hash(text: str) -> str:
    """게시글 본문의 SHA-256 해시값을 생성합니다."""
    if not text:
        return ""
    # 미세한 공백 차이로 인한 중복 방지를 위해 공백 제거 후 해싱
    clean_text = safe_re_sub_space(text)
    return hashlib.sha256(clean_text.encode('utf-8')).hexdigest()

def fetch_coordinates_kakao(address: str, api_key: str) -> Tuple[float, float]:
    """카카오 API를 사용하여 주소를 위경도 좌표로 변환합니다."""
    if not api_key:
        return 0.0, 0.0
    url = "https://dapi.kakao.com/v2/local/search/address.json"
    headers = {"Authorization": f"KakaoAK {api_key}"}
    try:
        resp = requests.get(url, headers=headers, params={"query": address}, timeout=5)
        if resp.status_code == 200:
            docs = resp.json().get("documents", [])
            if docs:
                return float(docs[0].get("y", 0.0)), float(docs[0].get("x", 0.0))
    except Exception as e:
        print(f"Kakao API Error for {address}: {e}")
    return 0.0, 0.0

def get_or_create_crawler_user(cur) -> int:
    """crawler_bot 사용자를 조회하거나 없으면 생성합니다."""
    cur.execute("SELECT user_id FROM users WHERE google_id = 'crawler_bot'")
    row = cur.fetchone()
    if row:
        return row[0]
    now = datetime.now()
    cur.execute("""
        INSERT INTO users (email, nickname, google_id, created_at, status_cd)
        VALUES ('crawler@sk.com', 'Data Crawler', 'crawler_bot', %s, %s)
        RETURNING user_id
    """, (now, Status.ACTIVE.value))
    return cur.fetchone()[0]

def archive_files(files: List[str], archive_dir: str) -> None:
    """임시 파일을 삭제하지 않고 archives 폴더로 이동하여 보관합니다."""
    path = Path(archive_dir)
    path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    for f_str in files:
        f = Path(f_str)
        if f.exists():
            try:
                # 파일명 뒤에 타임스탬프 추가하여 중복 방지
                dest = path / f"{f.stem}_{timestamp}{f.suffix}"
                shutil.move(str(f), str(dest))
                print(f"📦 아카이빙 완료: {f.name} -> {dest.name}")
            except Exception as e:
                print(f"⚠️ 아카이빙 실패 {f.name}: {e}")

def get_project_root() -> Path:
    """프로젝트 루트 경로를 반환합니다."""
    return Path(__file__).resolve().parent
