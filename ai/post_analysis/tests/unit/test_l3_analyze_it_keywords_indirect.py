"""PA-L3-ITKW: IC02 회사/감성 처리 오케스트레이션 테스트."""

import logging
from unittest.mock import MagicMock, patch

import analyze_it_keywords as itkw
import pandas as pd
import pytest

from analyze_it_keywords import analyze_it_keywords
from common.constant import AnalysisColumn, CodeTable


def _analysis_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            AnalysisColumn.CRAWLING_ID.value: [101, 102, 103, 104],
            AnalysisColumn.TITLE.value: [
                "OpenAI updates ChatGPT",
                "Meal B",
                "NVIDIA ships GPU update",
                "",
            ],
            AnalysisColumn.CONTENT.value: [
                "ChatGPT 개발사가 새 모델을 공개했다.",
                "meal review",
                "NVIDIA GPU platform update",
                "",
            ],
            AnalysisColumn.KEYWORDS.value: [pd.NA, pd.NA, "#existing", pd.NA],
            AnalysisColumn.INFORMATION_CD.value: [
                CodeTable.INFORMATION_IT_INFO.value,
                CodeTable.INFORMATION_RESTAURANT.value,
                CodeTable.INFORMATION_IT_INFO.value,
                CodeTable.INFORMATION_IT_INFO.value,
            ],
            AnalysisColumn.SENTIMENTAL.value: [pd.NA, pd.NA, "positive", pd.NA],
            AnalysisColumn.SCORE.value: [pd.NA, pd.NA, 0.8, pd.NA],
        }
    )


@patch("analyze_it_keywords.merge_analysis_data")
@patch("analyze_it_keywords.BertTokenizer")
@patch("analyze_it_keywords.get_it_keyword_target_data")
def test_pa_l3_itkw_001_processes_ic02_missing_sentiment_only(
    mock_get_targets: MagicMock,
    mock_tokenizer_cls: MagicMock,
    mock_merge: MagicMock,
) -> None:
    """기본 실행은 감성 결측 IC02 row만 회사 키워드와 제목 감성으로 MERGE한다."""
    mock_get_targets.return_value = _analysis_df()
    tokenizer = MagicMock()
    tokenizer.predict_sentiment.return_value = {"sentimental": "positive", "score": 0.91}
    mock_tokenizer_cls.return_value = tokenizer

    analyze_it_keywords()

    mock_get_targets.assert_called_once_with(overwrite=False, max_rows=None)
    tokenizer.predict_sentiment.assert_called_once_with("OpenAI updates ChatGPT")
    mock_merge.assert_called_once()
    df = mock_merge.call_args[0][0]
    assert list(df.columns) == [
        AnalysisColumn.CRAWLING_ID.value,
        AnalysisColumn.KEYWORDS.value,
        AnalysisColumn.SENTIMENTAL.value,
        AnalysisColumn.SCORE.value,
    ]
    assert df[AnalysisColumn.CRAWLING_ID.value].tolist() == [101]
    assert df[AnalysisColumn.KEYWORDS.value].iloc[0] == "#OpenAI#ai_company"
    assert df[AnalysisColumn.SENTIMENTAL.value].iloc[0] == "positive"
    assert df[AnalysisColumn.SCORE.value].iloc[0] == 0.91


@patch("analyze_it_keywords.merge_analysis_data")
@patch("analyze_it_keywords.BertTokenizer")
@patch("analyze_it_keywords.get_it_keyword_target_data")
def test_pa_l3_itkw_002_overwrite_reprocesses_valid_ic02_rows(
    mock_get_targets: MagicMock,
    mock_tokenizer_cls: MagicMock,
    mock_merge: MagicMock,
) -> None:
    """overwrite=True이면 유효 IC02 row의 제목 감성과 회사 키워드를 다시 계산한다."""
    mock_get_targets.return_value = _analysis_df()
    tokenizer = MagicMock()
    tokenizer.predict_sentiment.return_value = {"sentimental": "negative", "score": 0.77}
    mock_tokenizer_cls.return_value = tokenizer

    analyze_it_keywords(overwrite=True)

    assert tokenizer.predict_sentiment.call_count == 2
    df = mock_merge.call_args[0][0]
    assert df[AnalysisColumn.CRAWLING_ID.value].tolist() == [101, 103]
    assert df[AnalysisColumn.KEYWORDS.value].tolist() == [
        "#OpenAI#ai_company",
        "#NVIDIA#semiconductor",
    ]


@patch("analyze_it_keywords.merge_analysis_data")
@patch("analyze_it_keywords.BertTokenizer")
@patch("analyze_it_keywords.get_it_keyword_target_data")
def test_pa_l3_itkw_003_unmatched_company_preserves_existing_keywords(
    mock_get_targets: MagicMock,
    mock_tokenizer_cls: MagicMock,
    mock_merge: MagicMock,
) -> None:
    """회사 매칭이 없으면 keywords는 None으로 보내 기존 DB 값을 보존한다."""
    mock_get_targets.return_value = pd.DataFrame(
        {
            AnalysisColumn.CRAWLING_ID.value: [201],
            AnalysisColumn.TITLE.value: ["Open source release"],
            AnalysisColumn.CONTENT.value: ["No registered company name"],
            AnalysisColumn.KEYWORDS.value: ["#existing"],
            AnalysisColumn.INFORMATION_CD.value: [CodeTable.INFORMATION_IT_INFO.value],
            AnalysisColumn.SENTIMENTAL.value: [pd.NA],
            AnalysisColumn.SCORE.value: [pd.NA],
        }
    )
    tokenizer = MagicMock()
    tokenizer.predict_sentiment.return_value = {"sentimental": "positive", "score": 0.66}
    mock_tokenizer_cls.return_value = tokenizer

    analyze_it_keywords()

    df = mock_merge.call_args[0][0]
    assert df[AnalysisColumn.KEYWORDS.value].iloc[0] is None
    assert df[AnalysisColumn.SENTIMENTAL.value].iloc[0] == "positive"


@patch("analyze_it_keywords.tqdm", create=True)
@patch("analyze_it_keywords.merge_analysis_data")
@patch("analyze_it_keywords.BertTokenizer")
@patch("analyze_it_keywords.get_it_keyword_target_data")
def test_pa_l3_itkw_004_does_not_use_progress_bar(
    mock_get_targets: MagicMock,
    mock_tokenizer_cls: MagicMock,
    mock_merge: MagicMock,
    mock_tqdm: MagicMock,
) -> None:
    """기본 IC02 처리는 진행바를 사용하지 않는다."""
    mock_get_targets.return_value = _analysis_df()
    tokenizer = MagicMock()
    tokenizer.predict_sentiment.return_value = {"sentimental": "positive", "score": 0.9}
    mock_tokenizer_cls.return_value = tokenizer

    analyze_it_keywords()

    mock_tqdm.assert_not_called()


@patch("analyze_it_keywords.merge_analysis_data")
@patch("analyze_it_keywords.BertTokenizer")
@patch("analyze_it_keywords.get_it_keyword_target_data")
def test_pa_l3_itkw_005_normal_success_does_not_log_info(
    mock_get_targets: MagicMock,
    mock_tokenizer_cls: MagicMock,
    mock_merge: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """정상 처리에서는 INFO 진행도/요약 로그를 남기지 않는다."""
    mock_get_targets.return_value = _analysis_df()
    tokenizer = MagicMock()
    tokenizer.predict_sentiment.return_value = {"sentimental": "positive", "score": 0.9}
    mock_tokenizer_cls.return_value = tokenizer

    analyze_it_keywords()

    assert [record for record in caplog.records if record.levelname == "INFO"] == []


def test_pa_l3_itkw_008_cli_logging_suppresses_dependency_info(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLI 실행 시 외부 라이브러리 INFO 로그가 노출되지 않도록 설정한다."""
    basic_config = MagicMock()
    monkeypatch.setattr(logging, "basicConfig", basic_config)

    itkw._configure_cli_logging()

    basic_config.assert_called_once_with(
        level=logging.INFO,
        format="%(levelname)s [%(name)s] %(message)s",
    )
    for logger_name in ("httpx", "httpcore", "huggingface_hub", "transformers"):
        assert logging.getLogger(logger_name).level >= logging.WARNING


@patch("analyze_it_keywords.merge_analysis_data")
@patch("analyze_it_keywords.BertTokenizer")
@patch("analyze_it_keywords.get_it_keyword_target_data")
def test_pa_l3_itkw_006_row_failure_merges_successes_only(
    mock_get_targets: MagicMock,
    mock_tokenizer_cls: MagicMock,
    mock_merge: MagicMock,
) -> None:
    """row 단위 감성 실패는 ERROR로 기록하고 성공 row만 MERGE한다."""
    mock_get_targets.return_value = pd.DataFrame(
        {
            AnalysisColumn.CRAWLING_ID.value: [301, 302],
            AnalysisColumn.TITLE.value: ["OpenAI update", "NVIDIA update"],
            AnalysisColumn.CONTENT.value: ["OpenAI content", "NVIDIA content"],
            AnalysisColumn.KEYWORDS.value: [pd.NA, pd.NA],
            AnalysisColumn.INFORMATION_CD.value: [CodeTable.INFORMATION_IT_INFO.value] * 2,
            AnalysisColumn.SENTIMENTAL.value: [pd.NA, pd.NA],
            AnalysisColumn.SCORE.value: [pd.NA, pd.NA],
        }
    )
    tokenizer = MagicMock()
    tokenizer.predict_sentiment.side_effect = [
        RuntimeError("model failed"),
        {"sentimental": "negative", "score": 0.7},
    ]
    mock_tokenizer_cls.return_value = tokenizer

    analyze_it_keywords()

    df = mock_merge.call_args[0][0]
    assert df[AnalysisColumn.CRAWLING_ID.value].tolist() == [302]
    assert df[AnalysisColumn.KEYWORDS.value].iloc[0] == "#NVIDIA#semiconductor"


@patch("analyze_it_keywords.merge_analysis_data")
@patch("analyze_it_keywords.BertTokenizer")
@patch("analyze_it_keywords.get_it_keyword_target_data")
def test_pa_l3_itkw_007_missing_columns_raises_before_model_load(
    mock_get_targets: MagicMock,
    mock_tokenizer_cls: MagicMock,
    mock_merge: MagicMock,
) -> None:
    """필수 column이 없으면 모델 로드와 MERGE를 수행하지 않는다."""
    mock_get_targets.return_value = pd.DataFrame({AnalysisColumn.TITLE.value: ["A"]})

    with pytest.raises(ValueError, match="IT"):
        analyze_it_keywords()

    mock_tokenizer_cls.assert_not_called()
    mock_merge.assert_not_called()
