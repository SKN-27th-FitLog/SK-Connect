"""
utils/logger.py — 프로젝트 로깅 설정 유틸리티

모든 모듈에서 사용하는 통합 로거를 생성합니다.
로그는 콘솔(stdout)과 파일(logs/app.log) 양쪽에 출력됩니다.

[사용법]
    from utils.logger import get_logger
    logger = get_logger("ModuleName")
    logger.info("메시지")

[로그 출력 위치]
    - 콘솔 : 실시간 디버깅용
    - logs/app.log : 영구 저장 (운영/감사 추적용)

[설계 원칙]
    - 핸들러 중복 등록 방지: logger.handlers 체크
    - propagate=False: 루트 로거로 전파하지 않아 중복 출력 방지
    - 앱 로그와 Neo4j 로그를 분리하여 관리
"""

import logging
import sys
import os

from config.settings import settings


def get_logger(name: str) -> logging.Logger:
    """
    지정된 이름으로 로거를 생성하거나 기존 로거를 반환합니다.

    최초 호출 시에만 핸들러(콘솔 + 파일)를 등록합니다.
    이후 동일한 이름으로 호출하면 이미 설정된 로거를 그대로 반환합니다.

    Args:
        name: 로거 이름 (보통 모듈명. 예: "ParserNode", "Neo4jClient")

    Returns:
        설정된 logging.Logger 인스턴스

    로그 포맷:
        2026-04-19 18:00:00 [INFO] ParserNode: 메시지 내용
    """
    logger = logging.getLogger(name)

    # 핸들러가 이미 등록되어 있으면 중복 등록하지 않음
    if not logger.handlers:
        logger.setLevel(logging.INFO)

        # 로그 디렉토리 생성 (config/settings.py에서 경로를 읽음)
        log_dir = settings.LOG_DIR
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        log_file = os.path.join(log_dir, "app.log")

        # 1. 콘솔 출력 핸들러 (실시간 디버깅)
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(logging.INFO)

        # 2. 파일 저장 핸들러 (영구 기록)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.INFO)

        # 공통 포맷 설정
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        stream_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        logger.addHandler(stream_handler)
        logger.addHandler(file_handler)

        # 루트 로거로의 전파 차단 (중복 출력 방지)
        logger.propagate = False

    return logger
