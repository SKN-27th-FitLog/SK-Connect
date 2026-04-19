from __future__ import annotations

import csv
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


STAGE_ROOT = Path(__file__).resolve().parents[1]
IT_NEWS_ROOT = STAGE_ROOT.parent
REPO_ROOT = STAGE_ROOT.parents[2]


######################
# 스테이지 경로 관리 관련
######################
@dataclass(frozen=True)
class StagePaths:
    """
    crawling 단계의 성공/실패 출력 디렉터리를 묶어 보관한다.

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


def source_csv_path(paths: StagePaths, source: str, run_at: datetime, *, ok: bool) -> Path:
    """
    소스 이름과 실행 시각을 조합해 결과 CSV 경로를 계산한다.

    Args:
        paths: 스테이지 디렉터리 정보.
        source: 수집 소스 이름.
        run_at: 실행 기준 시각.
        ok: 성공 결과 저장 여부.

    Returns:
        최종 CSV 파일 경로.
    """
    target_dir = paths.success_dir if ok else paths.fail_dir
    return target_dir / f"{source}_{run_at.strftime('%H%M%S')}.csv"


######################
# CSV 입출력 및 외부 스크립트 실행 관련
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


def write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
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


def run_python(script_path: Path, *args: str) -> None:
    """
    레거시 수집 스크립트를 현재 파이썬 인터프리터로 실행한다.

    Args:
        script_path: 실행할 파이썬 스크립트 경로.
        *args: 스크립트에 전달할 추가 인자들.

    Raises:
        FileNotFoundError: 대상 스크립트가 없을 때 발생한다.
        subprocess.CalledProcessError: 스크립트 실행이 실패하면 발생한다.
    """
    if not script_path.is_file():
        raise FileNotFoundError(f"script not found: {script_path}")
    subprocess.run(
        [sys.executable, str(script_path), *args],
        cwd=REPO_ROOT,
        check=True,
    )


######################
# 수집 결과 검증 및 분리 관련
######################
def split_rows(
    rows: list[dict[str, str]],
    *,
    required_fields: tuple[str, ...],
    url_field: str,
    id_field: str,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """
    수집 결과를 필수 값 충족 여부에 따라 성공/실패 행으로 분리한다.

    Args:
        rows: 판별할 원본 행 목록.
        required_fields: 호출부에서 의미상 요구하는 필드 목록.
        url_field: URL 필드명.
        id_field: 고유 식별자 필드명.

    Returns:
        성공 행 목록과 실패 행 목록.
    """
    success_rows: list[dict[str, str]] = []
    fail_rows: list[dict[str, str]] = []

    for row in rows:
        normalized = dict(row)
        reasons: list[str] = []
        if normalized.get("state") != "ok":
            reasons.append("state_not_ok")

        if not (normalized.get(id_field) or "").strip():
            reasons.append(f"missing_{id_field}")

        if not (normalized.get("title") or "").strip():
            reasons.append("missing_title")

        if not (normalized.get("content") or "").strip():
            reasons.append("missing_content")

        if not (normalized.get(url_field) or "").strip():
            reasons.append(f"missing_{url_field}")

        if reasons:
            normalized["failure_reason"] = "|".join(reasons)
            fail_rows.append(normalized)
        else:
            success_rows.append(normalized)

    return success_rows, fail_rows
