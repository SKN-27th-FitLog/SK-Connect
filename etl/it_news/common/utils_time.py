from datetime import datetime


def get_run_time() -> datetime:
    """실행 기준 시간을 생성"""
    return datetime.now()


def format_hhmmss(dt: datetime) -> str:
    """HHMMSS 형태 문자열 반환"""
    return dt.strftime("%H%M%S")
