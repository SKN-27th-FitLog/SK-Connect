"""
crawling 스테이지 전용 설정 로더.

이 모듈은 `crawling/.env`와 `crawling/config.json`을 읽어
실행 코드가 동일한 방식으로 설정값을 참조하도록 만든다.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any


######################
# 스테이지 설정 파일 경로 관련
######################
# 모든 설정 조회는 현재 스테이지 폴더를 기준으로만 수행한다.
STAGE_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = STAGE_ROOT / ".env"
CONFIG_PATH = STAGE_ROOT / "config.json"


######################
# .env 파싱 보조 관련
######################
def _strip_inline_comment(raw: str) -> str:
    """
    `.env` 값 뒤에 붙은 인라인 주석을 제거한다.

    작은따옴표/큰따옴표 안의 `#`는 실제 값으로 취급하고,
    따옴표 밖의 `#`부터만 주석으로 잘라낸다.
    """
    in_single = False
    in_double = False
    pieces: list[str] = []

    for char in raw:
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == "#" and not in_single and not in_double:
            break
        pieces.append(char)
    return "".join(pieces).strip()


def _normalize_env_value(raw: str) -> str:
    """
    `.env` 원시 값을 실행 코드에서 쓰기 좋은 문자열로 정리한다.

    공백과 인라인 주석을 제거하고, 값이 따옴표로 감싸져 있으면
    양 끝 따옴표를 벗겨 실제 payload만 반환한다.
    """
    value = _strip_inline_comment(raw.strip())
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


@lru_cache(maxsize=1)
def load_stage_env() -> dict[str, str]:
    """
    현재 스테이지 폴더의 `.env` 파일을 한 번만 읽어 캐시한다.

    파일이 없으면 빈 딕셔너리를 반환해, 호출부가 기본값이나
    OS 환경변수 fallback을 자연스럽게 처리할 수 있게 한다.
    """
    if not ENV_PATH.is_file():
        return {}

    values: dict[str, str] = {}
    for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, raw_value = line.split("=", 1)
        values[name.strip()] = _normalize_env_value(raw_value)
    return values


def env(name: str, default: str = "") -> str:
    """
    스테이지 `.env`와 OS 환경변수를 우선순위대로 조회한다.

    우선순위:
    1. 현재 스테이지 폴더의 `.env`
    2. 이미 주입된 OS 환경변수
    3. 호출부가 넘긴 기본값
    """
    file_value = load_stage_env().get(name)
    if file_value not in (None, ""):
        return file_value

    runtime_value = os.environ.get(name)
    if runtime_value not in (None, ""):
        return runtime_value
    return default


@lru_cache(maxsize=1)
def get_config() -> dict[str, Any]:
    """
    현재 스테이지의 `config.json`을 읽어 캐시한다.

    설정 파일이 없으면 즉시 예외를 발생시켜, 실행 초기에
    잘못된 배포/복사 상태를 빠르게 드러내도록 한다.
    """
    if not CONFIG_PATH.is_file():
        raise FileNotFoundError(f"config.json not found: {CONFIG_PATH}")
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
