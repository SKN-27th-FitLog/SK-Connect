import os
import sys
import re
import shutil
import requests
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set, Any, Final
from datetime import datetime

import pandas as pd

# members 모듈 임포트를 위한 시스템 경로 설정
PROJECT_ROOT_PATH: Final[Path] = Path(__file__).resolve().parent
if str(PROJECT_ROOT_PATH) not in sys.path:
    sys.path.append(str(PROJECT_ROOT_PATH))

try:
    from members import Status
except ImportError:
    class Status: 
        ACTIVE = "ST01"

def setup_logger(name: str = "ETL_Logger") -> logging.Logger:
    """
    중앙 집중형 로거를 설정합니다. 모든 스크립트는 이 로거를 통해 로그를 남깁니다.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s', '%Y-%m-%d %H:%M:%S')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

# 기본 로거 초기화
logger: logging.Logger = setup_logger()

def normalize_string(text: Optional[str]) -> str:
    """
    텍스트 정규화: 특수문자 및 공백을 제거하고 소문자로 변환합니다.
    """
    if not text:
        return ""
    text = re.sub(r'[^가-힣a-zA-Z0-9]', '', text)
    return text.lower()

def safe_re_sub_space(text: Optional[str]) -> str:
    """
    모든 종류의 공백을 제거합니다.
    """
    if not text:
        return ""
    return re.sub(r'\s+', '', str(text))

def generate_content_hash(text: Optional[str]) -> str:
    """
    본문 내용에 대한 SHA-256 해시값을 생성합니다.
    """
    if not text:
        return ""
    clean_text = safe_re_sub_space(text)
    return hashlib.sha256(clean_text.encode('utf-8')).hexdigest()

def fetch_coordinates_kakao(address: str, api_key: str) -> Tuple[float, float]:
    """
    카카오 로컬 API를 사용하여 주소를 위도/경도 좌표로 변환합니다.
    """
    if not api_key:
        logger.warning("카카오 API 키가 설정되지 않았습니다.")
        return 0.0, 0.0
        
    url: str = "https://dapi.kakao.com/v2/local/search/address.json"
    headers: Dict[str, str] = {"Authorization": f"KakaoAK {api_key}"}
    
    try:
        resp = requests.get(url, headers=headers, params={"query": address}, timeout=5)
        if resp.status_code == 200:
            data: Dict[str, Any] = resp.json()
            docs: List[Dict[str, Any]] = data.get("documents", [])
            if docs:
                return float(docs[0].get("y", 0.0)), float(docs[0].get("x", 0.0))
        else:
            logger.error(f"카카오 API 호출 실패 (Status: {resp.status_code})")
    except Exception as e:
        logger.error(f"카카오 API 호출 오류 ({address}): {str(e)}")
        
    return 0.0, 0.0

def get_or_create_crawler_user(cur: Any) -> int:
    """
    시스템 계정인 'crawler_bot' 사용자를 조회하거나 신규 생성합니다.
    cur 인자는 psycopg2 cursor 객체여야 합니다.
    """
    cur.execute("SELECT user_id FROM users WHERE google_id = 'crawler_bot'")
    row: Optional[Tuple[int]] = cur.fetchone()
    if row:
        return row[0]
    
    now: datetime = datetime.now()
    cur.execute("""
        INSERT INTO users (email, nickname, google_id, created_at, status_cd)
        VALUES ('crawler@sk.com', 'Data Crawler', 'crawler_bot', %s, %s)
        RETURNING user_id
    """, (now, Status.ACTIVE.value))
    
    res: Optional[Tuple[int]] = cur.fetchone()
    if not res:
        raise RuntimeError("사용자 생성 실패")
    return res[0]

def get_hive_path(process: str, service: str, status: str = "success", extension: str = ".csv") -> Path:
    """
    하이브 스타일(key=value)의 계층적 디렉토리 경로를 생성합니다.
    """
    now: datetime = datetime.now()
    year: str = now.strftime("%Y")
    month: str = now.strftime("%m")
    day: str = now.strftime("%d")
    timestamp: str = now.strftime("%H%M%S")
    
    path: Path = Path(process) / service / f"year={year}" / f"month={month}" / f"day={day}" / f"status={status}"
    full_dir: Path = get_project_root() / path
    full_dir.mkdir(parents=True, exist_ok=True)
    
    return full_dir / f"{timestamp}{extension}"

def cleanup_and_log_files(files: List[str], log_filename: str = "cleanup_summary.csv") -> None:
    """
    성공적으로 처리된 임시 파일들을 삭제하고 이력을 로그 파일에 기록합니다.
    """
    project_root: Path = get_project_root()
    log_path: Path = project_root / log_filename
    
    timestamp: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    records: List[Dict[str, Any]] = []
    
    for f_str in files:
        f: Path = Path(f_str)
        if f.exists():
            try:
                size: int = f.stat().st_size
                f.unlink()
                records.append({
                    "timestamp": timestamp,
                    "filename": f.name,
                    "size_bytes": size,
                    "status": "DELETED"
                })
                logger.info(f"🗑️ 자동 삭제 완료: {f.name}")
            except Exception as e:
                logger.error(f"⚠️ 삭제 실패 {f.name}: {str(e)}")
    
    if records:
        df: pd.DataFrame = pd.DataFrame(records)
        header: bool = not log_path.exists()
        df.to_csv(log_path, mode='a', index=False, header=header, encoding='utf-8-sig')
        logger.info(f"📝 삭제 이력 기록됨: {log_path.name}")

def get_project_root() -> Path:
    """
    프로젝트의 루트 경로를 반환합니다.
    """
    return Path(__file__).resolve().parent

def ensure_dir(path: Path) -> None:
    """
    지정된 경로의 부모 디렉토리가 존재하지 않으면 생성합니다.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
