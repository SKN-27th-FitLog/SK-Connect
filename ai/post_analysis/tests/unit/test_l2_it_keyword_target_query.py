"""PA-L2-ITKW-PG: IC02 회사/감성 대상 조회 SQL 계약."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from common.constant import AnalysisColumn, CodeTable
from postgresql.run_query import get_it_keyword_target_data


def _mock_db_with_cursor(rows: list[tuple] | None = None) -> tuple[MagicMock, MagicMock]:
    """PostgreDB cursor context manager mock을 만든다."""
    cursor = MagicMock()
    cursor.description = [
        SimpleNamespace(name=AnalysisColumn.CRAWLING_ID.value),
        SimpleNamespace(name=AnalysisColumn.TITLE.value),
        SimpleNamespace(name=AnalysisColumn.CONTENT.value),
        SimpleNamespace(name=AnalysisColumn.KEYWORDS.value),
        SimpleNamespace(name=AnalysisColumn.INFORMATION_CD.value),
        SimpleNamespace(name=AnalysisColumn.SENTIMENTAL.value),
        SimpleNamespace(name=AnalysisColumn.SCORE.value),
    ]
    cursor.fetchall.return_value = rows or []

    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor

    db = MagicMock()
    db.conn = conn
    return db, cursor


@patch("postgresql.run_query.PostgreDB")
def test_pa_l2_itkw_pg_001_pending_query_filters_ic02_missing_sentiment_or_score(
    mock_postgres: MagicMock,
) -> None:
    """기본 조회는 IC02, 유효 title/content, 감성 결측 조건을 SQL에서 먼저 거른다."""
    db, cursor = _mock_db_with_cursor()
    mock_postgres.return_value = db

    df = get_it_keyword_target_data(overwrite=False, max_rows=5)

    sql, params = cursor.execute.call_args.args
    assert "FROM analysis AS a" in sql
    assert "LEFT JOIN crawling AS c" not in sql
    assert "a.information_cd = %s" in sql
    assert "(a.sentimental IS NULL OR BTRIM(a.sentimental) = '')" in sql
    assert "a.score IS NULL" in sql
    assert "BTRIM(a.keywords)" not in sql
    assert "LIMIT %s" in sql
    assert CodeTable.INFORMATION_IT_INFO.value in params
    assert 5 in params
    assert list(df.columns) == [
        AnalysisColumn.CRAWLING_ID.value,
        AnalysisColumn.TITLE.value,
        AnalysisColumn.CONTENT.value,
        AnalysisColumn.KEYWORDS.value,
        AnalysisColumn.INFORMATION_CD.value,
        AnalysisColumn.SENTIMENTAL.value,
        AnalysisColumn.SCORE.value,
    ]


@patch("postgresql.run_query.PostgreDB")
def test_pa_l2_itkw_pg_002_overwrite_query_keeps_ic02_and_text_filters_only(
    mock_postgres: MagicMock,
) -> None:
    """overwrite=True는 감성 결측 조건 없이 유효 IC02 row를 재처리한다."""
    db, cursor = _mock_db_with_cursor()
    mock_postgres.return_value = db

    get_it_keyword_target_data(overwrite=True)

    sql, params = cursor.execute.call_args.args
    assert "a.information_cd = %s" in sql
    assert "a.sentimental IS NULL" not in sql
    assert "a.score IS NULL" not in sql
    assert "BTRIM(a.keywords)" not in sql
    assert "LEFT JOIN crawling AS c" not in sql
    assert "LIMIT %s" not in sql
    assert CodeTable.INFORMATION_IT_INFO.value in params
