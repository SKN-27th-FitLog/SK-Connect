from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

try:
    import psycopg
except Exception:  # pragma: no cover - optional until runtime
    psycopg = None


STAGE_ROOT = Path(__file__).resolve().parents[1]
IT_NEWS_ROOT = STAGE_ROOT.parent
CRAWLING_ROOT = IT_NEWS_ROOT / "crawling"


######################
# 스테이지 경로 관리 관련
######################
@dataclass(frozen=True)
class StagePaths:
    """
    cleaning 단계의 성공/실패 출력 디렉터리를 묶어 보관한다.

    Attributes:
        success_dir: 성공 결과 CSV 저장 디렉터리.
        fail_dir: 실패 결과 CSV 저장 디렉터리.
    """
    success_dir: Path
    fail_dir: Path


def make_stage_paths(bucket: str, run_at: datetime, *, kind: str | None = None) -> StagePaths:
    """
    실행 일자 기준으로 스테이지의 성공/실패 디렉터리를 생성한다.

    Args:
        bucket: 생성할 하위 버킷 이름.
        run_at: 실행 기준 시각.

    Returns:
        생성된 디렉터리 경로 정보를 담은 StagePaths 객체.
    """
    base = STAGE_ROOT / bucket
    if kind:
        base = base / kind
    base = base / run_at.strftime("%Y") / run_at.strftime("%m") / run_at.strftime("%d")
    success_dir = base / "success"
    fail_dir = base / "fail"
    success_dir.mkdir(parents=True, exist_ok=True)
    fail_dir.mkdir(parents=True, exist_ok=True)
    return StagePaths(success_dir=success_dir, fail_dir=fail_dir)


def source_csv_path(paths: StagePaths, filename: str, *, ok: bool) -> Path:
    """
    성공/실패 여부에 따라 대상 CSV 저장 경로를 계산한다.

    Args:
        paths: 스테이지 디렉터리 정보.
        filename: 저장할 파일명.
        ok: 성공 결과 저장 여부.

    Returns:
        최종 CSV 파일 경로.
    """
    target_dir = paths.success_dir if ok else paths.fail_dir
    return target_dir / filename


######################
# CSV 입출력 및 원본 파일 조회 관련
######################
def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """
    CSV 파일을 읽어 헤더와 행 목록을 함께 반환한다.

    Args:
        path: 읽을 CSV 파일 경로.

    Returns:
        필드명 목록과 행 데이터 목록.

    Raises:
        ValueError: CSV 헤더가 없을 때 발생한다.
    """
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"CSV header is missing: {path}")
        return list(reader.fieldnames), list(reader)


def write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    """
    지정한 필드 순서대로 CSV 파일을 생성한다.

    Args:
        path: 저장할 CSV 파일 경로.
        fieldnames: CSV 헤더 순서.
        rows: 저장할 행 데이터 목록.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def raw_success_files(run_at: datetime, *, kind: str | None = None) -> list[Path]:
    """
    지정한 날짜의 crawling 성공 결과 CSV 목록을 조회한다.

    Args:
        run_at: 조회 기준 실행 시각.

    Returns:
        성공 디렉터리에 있는 CSV 파일 경로 목록.
    """
    base = CRAWLING_ROOT / "raw"
    if kind:
        base = base / kind
    base = base / run_at.strftime("%Y") / run_at.strftime("%m") / run_at.strftime("%d") / "success"
    if not base.is_dir():
        return []
    return sorted(base.glob("*.csv"))


######################
# 환경 변수 및 증분 기준 시각 조회 관련
######################
def _env(name: str, default: str) -> str:
    """
    환경 변수를 읽고 비어 있으면 기본값을 반환한다.

    Args:
        name: 환경 변수 이름.
        default: 기본값.

    Returns:
        환경 변수 값 또는 기본값.
    """
    value = os.environ.get(name)
    return value if value not in (None, "") else default


def fetch_last_created_at() -> datetime | None:
    """
    DB에 저장된 가장 최근 created_at 값을 조회한다.

    Args:
        없음.

    Returns:
        조회된 최신 created_at 또는 연결 실패 시 None.
    """
    if psycopg is None:
        return None

    params = {
        "host": _env("PGHOST", "localhost"),
        "port": int(_env("PGPORT", "5432")),
        "dbname": _env("PGDATABASE", "service"),
        "user": _env("PGUSER", "user"),
        "password": _env("PGPASSWORD", "password123"),
    }
    try:
        with psycopg.connect(**params, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT MAX("created_at") FROM "crawling"')
                row = cur.fetchone()
                return row[0] if row else None
    except Exception:
        return None


def fallback_cutoff(run_at: datetime) -> datetime:
    """
    DB 기준 시각을 조회하지 못할 때 사용할 기본 증분 기준 시각을 계산한다.

    Args:
        run_at: 현재 실행 시각.

    Returns:
        실행 시각 기준 90일 이전 시각.
    """
    return run_at - timedelta(days=90)
