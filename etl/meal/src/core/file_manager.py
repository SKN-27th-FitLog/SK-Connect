import logging
import sys
import os
import re
import time
import urllib.request
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Final, Any

class FileManager:
    """
    프로젝트의 파일 시스템, Hive 경로 관리 및 중앙 로깅을 담당합니다.
    """
    
    def __init__(self, logger_name: str = "ETL_Logger"):
        self.root = self._get_project_root()
        self.log_dir = self.root / "logs"
        self.log_dir.mkdir(exist_ok=True)
        self.logger = self._setup_logger(logger_name)
        self.safe_filename_pattern = re.compile(r"[^0-9a-zA-Z가-힣._-]+")

    def _get_project_root(self) -> Path:
        return Path(__file__).resolve().parent.parent.parent

    def _setup_logger(self, name: str) -> logging.Logger:
        logger = logging.getLogger(name)
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            formatter = logging.Formatter(
                '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s', 
                '%Y-%m-%d %H:%M:%S'
            )
            stream_handler = logging.StreamHandler(sys.stdout)
            stream_handler.setFormatter(formatter)
            logger.addHandler(stream_handler)
            
            log_file = self.log_dir / f"etl_{datetime.now().strftime('%Y%m%d')}.log"
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        return logger

    def slugify(self, text: str, max_len: int = 80) -> str:
        text = re.sub(r"\s+", " ", str(text)).strip()
        text = self.safe_filename_pattern.sub("_", text)
        return text[:max_len] if text else "unknown"

    def download_image(self, url: str, folder_name: str, prefix: str = "img") -> Optional[str]:
        """이미지 URL을 다운로드하여 로컬에 저장하고 경로를 반환합니다."""
        if not url or not url.startswith("http"):
            return None
            
        try:
            target_dir = self.root / "data_lake" / "images" / self.slugify(folder_name)
            target_dir.mkdir(parents=True, exist_ok=True)
            
            ext = Path(url.split("?")[0]).suffix or ".jpg"
            if len(ext) > 5: ext = ".jpg" # 쿼리 스트링 등 방지
            
            save_path = target_dir / f"{prefix}_{int(time.time() * 1000)}{ext}"
            urllib.request.urlretrieve(url, str(save_path))
            return str(save_path)
        except Exception as e:
            self.logger.warning(f"--- 이미지 다운로드 실패 ({url}): {e}")
            return None

    def get_hive_path(self, process: str, service: str, status: str = "success") -> Path:
        p_name = process.split('=')[-1]
        s_name = service.split('=')[-1]
        now = datetime.now()
        path = self.root / f"process={p_name}" / f"service={s_name}" / \
               f"year={now.year}" / f"month={now.month:02d}" / f"day={now.day:02d}" / \
               f"status={status}"
        path.mkdir(parents=True, exist_ok=True)
        return path / f"{now.strftime('%H%M%S')}.csv"

    def save_df(self, df: Any, process: str, service: str, status: str = "success") -> Path:
        save_path = self.get_hive_path(process, service, status)
        df.to_csv(save_path, index=False, encoding="utf-8-sig")
        self.logger.info(f"--- [{process.upper()}] 파일 저장 완료 ({service}): {save_path.name} (status={status})")
        return save_path

# Singleton
file_manager = FileManager()
logger = file_manager.logger
