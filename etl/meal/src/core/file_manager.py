import logging
import sys
import os
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

    def _get_project_root(self) -> Path:
        # src/core/file_manager.py -> src/core -> src -> meal (root)
        return Path(__file__).resolve().parent.parent.parent

    def _setup_logger(self, name: str) -> logging.Logger:
        logger = logging.getLogger(name)
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            formatter = logging.Formatter(
                '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s', 
                '%Y-%m-%d %H:%M:%S'
            )
            
            # 콘솔 핸들러 (Windows encoding 이슈 방지를 위해 로깅 레벨 조정 가능)
            stream_handler = logging.StreamHandler(sys.stdout)
            stream_handler.setFormatter(formatter)
            logger.addHandler(stream_handler)
            
            # 파일 핸들러 (UTF-8 영구 저장)
            log_file = self.log_dir / f"etl_{datetime.now().strftime('%Y%m%d')}.log"
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
        return logger

    def get_hive_path(self, process: str, service: str, status: str = "success") -> Path:
        """
        절대 규칙: 하이브 스타일의 파티션 경로를 생성합니다.
        프로세스(raw, cleansing, save)와 서비스(shop, review, menu, map) 명칭을 엄격히 준수합니다.
        """
        p_name = process.split('=')[-1]
        s_name = service.split('=')[-1]
        
        now = datetime.now()
        path = self.root / f"process={p_name}" / f"service={s_name}" / \
               f"year={now.year}" / f"month={now.month:02d}" / f"day={now.day:02d}" / \
               f"status={status}"
        
        path.mkdir(parents=True, exist_ok=True)
        return path / f"{now.strftime('%H%M%S')}.csv"

    def save_df(self, df: Any, process: str, service: str, status: str = "success") -> Path:
        """
        DataFrame을 하이브 구조에 맞춰 저장하고 로깅합니다.
        """
        if df is None or (hasattr(df, 'empty') and df.empty):
            # 빈 데이터프레임이라도 헤더만 포함하여 저장 (파이프라인 유지를 위해)
            pass

        save_path = self.get_hive_path(process, service, status)
        df.to_csv(save_path, index=False, encoding="utf-8-sig")
        self.logger.info(f"--- [{process.upper()}] 파일 저장 완료 ({service}): {save_path.name}")
        return save_path

    def get_latest_file(self, process: str, service: str, status: str = "success") -> Optional[str]:
        """지정된 서비스의 가장 최근에 생성된 파일 경로를 반환합니다."""
        target_root = self.root / f"process={process}" / f"service={service}"
        if not target_root.exists():
            return None
        
        files = sorted(target_root.glob(f"**/*status={status}/*.csv"), reverse=True)
        return str(files[0]) if files else None

# Singleton-like instance for internal use
file_manager = FileManager()
logger = file_manager.logger
