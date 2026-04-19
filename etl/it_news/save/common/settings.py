"""
save 스테이지 전용 설정 로더.

이 모듈은 `save/.env`와 `save/config.json`을 읽어
DB 적재 단계에서 필요한 연결값과 저장 정책을 제공한다.
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
STAGE_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = STAGE_ROOT / ".env"
CONFIG_PATH = STAGE_ROOT / "config.json"


######################
# .env 파싱 보조 관련
######################
def _strip_inline_comment(raw: str) -> str:
    """`.env` 값 뒤의 인라인 주석을 제거해 실제 값만 남긴다."""
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
    """공백/주석/감싼 따옴표를 정리해 최종 문자열 값을 만든다."""
    value = _strip_inline_comment(raw.strip())
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


@lru_cache(maxsize=1)
def load_stage_env() -> dict[str, str]:
    """현재 스테이지 `.env` 내용을 캐시된 딕셔너리로 반환한다."""
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
    """스테이지 `.env`와 OS 환경변수에서 값을 조회하고 없으면 기본값을 반환한다."""
    file_value = load_stage_env().get(name)
    if file_value not in (None, ""):
        return file_value

    runtime_value = os.environ.get(name)
    if runtime_value not in (None, ""):
        return runtime_value
    return default


@lru_cache(maxsize=1)
def get_config() -> dict[str, Any]:
    """현재 스테이지 `config.json`을 읽어 캐시된 딕셔너리로 반환한다."""
    if not CONFIG_PATH.is_file():
        raise FileNotFoundError(f"config.json not found: {CONFIG_PATH}")
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
