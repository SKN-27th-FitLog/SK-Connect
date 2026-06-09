"""PA-L3-ITKW: analyze_it_keywords indirect tests for IC02 orchestration."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from analyze_it_keywords import ItKeywordResult, analyze_it_keywords, extract_it_keywords
from common.constant import AnalysisColumn, AnalyzeItKeywordsConfig, CodeTable, CrawlingColumn
from common.it_keyword_candidates import ItKeywordCandidate, extract_it_keyword_candidates


def _analysis_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            AnalysisColumn.CRAWLING_ID.value: [101, 102, 103, 104],
            AnalysisColumn.TITLE.value: ["IT A", "Meal B", "IT C", ""],
            AnalysisColumn.CONTENT.value: ["PyTorch update", "meal review", "GPU news", ""],
            AnalysisColumn.KEYWORDS.value: [pd.NA, pd.NA, "#existing", pd.NA],
            AnalysisColumn.INFORMATION_CD.value: [
                CodeTable.INFORMATION_IT_INFO.value,
                CodeTable.INFORMATION_RESTAURANT.value,
                CodeTable.INFORMATION_IT_INFO.value,
                CodeTable.INFORMATION_IT_INFO.value,
            ],
        }
    )


def _crawling_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            CrawlingColumn.CRAWLING_ID.value: [101, 103, 104],
            CrawlingColumn.VIEW_COUNT.value: [1200, 10, 999],
            CrawlingColumn.COMMENT_COUNT.value: [8, 0, 1],
            CrawlingColumn.POINT.value: [3, 0, 1],
        }
    )


def _candidate_terms() -> list[str]:
    """후보군 검증 테스트에 사용할 원문 내 영문 기술명 목록."""
    return [
        "PyTorch",
        "GPU",
        "API",
        "CUDA",
        "Kubernetes",
        "Terraform",
        "Docker",
        "Linux",
        "Python",
        "Rust",
        "Java",
        "Node",
    ]


@patch("analyze_it_keywords.merge_analysis_data")
@patch("analyze_it_keywords.extract_it_keywords")
@patch("analyze_it_keywords.get_it_keyword_target_data")
def test_pa_l3_itkw_001_processes_ic02_missing_keywords_only(
    mock_get_targets: MagicMock,
    mock_extract: MagicMock,
    mock_merge: MagicMock,
) -> None:
    """기본 실행은 IC02 중 keywords 결측이고 본문 또는 제목이 있는 row만 처리한다."""
    mock_get_targets.return_value = _analysis_df()
    mock_extract.return_value = ItKeywordResult(
        summary="summary",
        flow="release -> impact",
        interest_label="high",
        keywords=["PyTorch", "inference speed", "community interest"],
    )

    analyze_it_keywords()

    mock_extract.assert_called_once()
    mock_merge.assert_called_once()
    df = mock_merge.call_args[0][0]
    assert len(df) == 1
    assert list(df.columns) == [
        AnalysisColumn.CRAWLING_ID.value,
        AnalysisColumn.CONTENT.value,
        AnalysisColumn.KEYWORDS.value,
    ]
    assert df[AnalysisColumn.CRAWLING_ID.value].iloc[0] == 101
    assert df[AnalysisColumn.CONTENT.value].iloc[0] == "[본문]\nPyTorch update\n\n[요약]\nsummary"
    assert (
        df[AnalysisColumn.KEYWORDS.value].iloc[0]
        == "#PyTorch#inference speed#community interest"
    )


@patch("analyze_it_keywords.merge_analysis_data")
@patch("analyze_it_keywords.extract_it_keywords")
@patch("analyze_it_keywords.get_it_keyword_target_data")
def test_pa_l3_itkw_002_overwrite_reprocesses_existing_ic02(
    mock_get_targets: MagicMock,
    mock_extract: MagicMock,
    mock_merge: MagicMock,
) -> None:
    """overwrite=True이면 기존 IC02 keywords row도 재처리한다."""
    mock_get_targets.return_value = _analysis_df()
    mock_extract.return_value = ItKeywordResult(
        summary="summary",
        flow="release -> impact",
        interest_label="medium",
        keywords=["GPU", "developer impact"],
    )

    analyze_it_keywords(overwrite=True)

    assert mock_extract.call_count == 2
    mock_merge.assert_called_once()
    assert list(mock_merge.call_args[0][0][AnalysisColumn.CRAWLING_ID.value]) == [101, 103]


@patch("analyze_it_keywords.merge_analysis_data")
@patch("analyze_it_keywords.extract_it_keywords")
@patch("analyze_it_keywords.get_it_keyword_target_data")
def test_pa_l3_itkw_003_max_rows_limits_after_filter(
    mock_get_targets: MagicMock,
    mock_extract: MagicMock,
    mock_merge: MagicMock,
) -> None:
    """max_rows는 IC02 필터 이후 적용한다."""
    mock_get_targets.return_value = pd.DataFrame(
        {
            AnalysisColumn.CRAWLING_ID.value: [1, 2, 3],
            AnalysisColumn.TITLE.value: ["A", "B", "C"],
            AnalysisColumn.CONTENT.value: ["a", "b", "c"],
            AnalysisColumn.KEYWORDS.value: [pd.NA, pd.NA, pd.NA],
            AnalysisColumn.INFORMATION_CD.value: [CodeTable.INFORMATION_IT_INFO.value] * 3,
        }
    )
    mock_extract.return_value = ItKeywordResult(keywords=["keyword"])

    analyze_it_keywords(max_rows=2)

    assert mock_extract.call_count == 2
    assert len(mock_merge.call_args[0][0]) == 2


@patch("analyze_it_keywords.merge_analysis_data")
@patch("analyze_it_keywords.extract_it_keywords")
@patch("analyze_it_keywords.get_it_keyword_target_data")
def test_pa_l3_itkw_004_row_failure_merges_successes_only(
    mock_get_targets: MagicMock,
    mock_extract: MagicMock,
    mock_merge: MagicMock,
) -> None:
    """row 단위 실패는 계속 진행하고 성공분만 MERGE한다."""
    mock_get_targets.return_value = pd.DataFrame(
        {
            AnalysisColumn.CRAWLING_ID.value: [1, 2],
            AnalysisColumn.TITLE.value: ["A", "B"],
            AnalysisColumn.CONTENT.value: ["a", "b"],
            AnalysisColumn.KEYWORDS.value: [pd.NA, pd.NA],
            AnalysisColumn.INFORMATION_CD.value: [CodeTable.INFORMATION_IT_INFO.value] * 2,
        }
    )
    mock_extract.side_effect = [RuntimeError("ollama down"), ItKeywordResult(keywords=["success"])]

    analyze_it_keywords()

    mock_merge.assert_called_once()
    df = mock_merge.call_args[0][0]
    assert list(df[AnalysisColumn.CRAWLING_ID.value]) == [2]
    assert df[AnalysisColumn.KEYWORDS.value].iloc[0] == "#success"


@patch("analyze_it_keywords.merge_analysis_data")
@patch("analyze_it_keywords.extract_it_keywords")
@patch("analyze_it_keywords.get_it_keyword_target_data")
def test_pa_l3_itkw_005_no_success_skips_merge(
    mock_get_targets: MagicMock,
    mock_extract: MagicMock,
    mock_merge: MagicMock,
) -> None:
    """추출 결과가 모두 비어 있으면 MERGE하지 않는다."""
    mock_get_targets.return_value = pd.DataFrame(
        {
            AnalysisColumn.CRAWLING_ID.value: [1],
            AnalysisColumn.TITLE.value: ["A"],
            AnalysisColumn.CONTENT.value: ["a"],
            AnalysisColumn.KEYWORDS.value: [pd.NA],
            AnalysisColumn.INFORMATION_CD.value: [CodeTable.INFORMATION_IT_INFO.value],
        }
    )
    mock_extract.return_value = ItKeywordResult(keywords=[])

    analyze_it_keywords()

    mock_merge.assert_not_called()
@patch("analyze_it_keywords.merge_analysis_data")
@patch("analyze_it_keywords.extract_it_keywords")
@patch("analyze_it_keywords.get_it_keyword_target_data")
def test_pa_l3_itkw_006_missing_columns(
    mock_get_targets: MagicMock,
    mock_extract: MagicMock,
    mock_merge: MagicMock,
) -> None:
    """필수 column이 없으면 ValueError를 발생시키고 외부 호출은 하지 않는다."""
    mock_get_targets.return_value = pd.DataFrame({AnalysisColumn.TITLE.value: ["A"]})

    with pytest.raises(ValueError, match="IT"):
        analyze_it_keywords()

    mock_extract.assert_not_called()
    mock_merge.assert_not_called()


@patch("analyze_it_keywords._ollama_chat_json")
def test_pa_l3_itkw_007_extract_uses_ollama_json_response(
    mock_ollama_chat_json: MagicMock,
) -> None:
    """extract_it_keywords는 Ollama JSON dict를 ItKeywordResult로 검증한다."""
    candidate_terms = _candidate_terms()
    mock_ollama_chat_json.return_value = {
        "summary": "summary",
        "flow": "release -> impact",
        "interest_label": "high",
        "keywords": candidate_terms,
    }

    result = extract_it_keywords(
        {
            "title": "PyTorch GPU API",
            "content": " ".join([*candidate_terms, "update"]),
        }
    )

    mock_ollama_chat_json.assert_called_once()
    assert result == ItKeywordResult(
        summary="summary",
        flow="release -> impact",
        interest_label="high",
        keywords=candidate_terms,
    )


@patch("analyze_it_keywords._ollama_chat_json")
def test_pa_l3_itkw_007_1_extract_supplements_sparse_keywords_without_retry(
    mock_ollama_chat_json: MagicMock,
) -> None:
    """부족한 1차 LLM 결과는 2차 호출 없이 deterministic 후보 상위 항목으로 보강한다."""
    candidate_terms = _candidate_terms()
    title = "PyTorch GPU API"
    content = " ".join([*candidate_terms, "update"])
    mock_ollama_chat_json.return_value = {
        "summary": "summary",
        "flow": "release -> impact",
        "interest_label": "medium",
        "keywords": ["PyTorch", "GPU", "API"],
    }

    result = extract_it_keywords(
        {
            "title": title,
            "content": content,
        }
    )

    mock_ollama_chat_json.assert_called_once()
    assert result.keywords[:3] == ["PyTorch", "GPU", "API"]
    assert len(result.keywords) == AnalyzeItKeywordsConfig.MIN_KEYWORDS
    candidate_texts = {candidate.text for candidate in extract_it_keyword_candidates(title, content)}
    assert set(result.keywords).issubset(candidate_texts)


@patch("analyze_it_keywords._ollama_chat_json")
@patch("analyze_it_keywords._build_candidate_context")
def test_pa_l3_itkw_012_extract_skips_llm_for_confident_deterministic_candidates(
    mock_build_candidate_context: MagicMock,
    mock_ollama_chat_json: MagicMock,
) -> None:
    candidates = [
        ItKeywordCandidate(f"keyword-{index:02d}", 24 - index, "both", 2)
        for index in range(1, 16)
    ]
    mock_build_candidate_context.return_value = (candidates, "candidate prompt")

    result = extract_it_keywords({"title": "Agent update", "content": "Agent update content"})

    mock_ollama_chat_json.assert_not_called()
    assert result.keywords == [f"keyword-{index:02d}" for index in range(1, 13)]
    assert result.summary == ""


@patch("analyze_it_keywords._ollama_chat_json")
@patch("analyze_it_keywords._build_candidate_context")
def test_pa_l3_itkw_013_extract_maps_llm_keyword_ids_for_low_confidence_candidates(
    mock_build_candidate_context: MagicMock,
    mock_ollama_chat_json: MagicMock,
) -> None:
    candidates = [
        ItKeywordCandidate(f"keyword-{index:02d}", 10, "content", 1)
        for index in range(1, 16)
    ]
    mock_build_candidate_context.return_value = (candidates, "candidate prompt")
    mock_ollama_chat_json.return_value = {
        "summary": "summary",
        "flow": "release -> impact",
        "interest_label": "medium",
        "keyword_ids": [2, 1, 999, 2],
    }

    result = extract_it_keywords({"title": "Agent update", "content": "Agent update content"})

    mock_ollama_chat_json.assert_called_once()
    prompt = mock_ollama_chat_json.call_args[0][0]
    assert "keyword_ids" in prompt
    assert result.keywords[:2] == ["keyword-02", "keyword-01"]
    assert len(result.keywords) == AnalyzeItKeywordsConfig.MIN_KEYWORDS
    assert "keyword-999" not in result.keywords


@patch("analyze_it_keywords.merge_analysis_data")
@patch("analyze_it_keywords.extract_it_keywords")
@patch("analyze_it_keywords.get_it_keyword_target_data")
def test_pa_l3_itkw_011_blank_summary_keeps_keyword_only_merge(
    mock_get_targets: MagicMock,
    mock_extract: MagicMock,
    mock_merge: MagicMock,
) -> None:
    """요약이 비어 있으면 content를 merge payload에 포함하지 않는다."""
    mock_get_targets.return_value = pd.DataFrame(
        {
            AnalysisColumn.CRAWLING_ID.value: [701],
            AnalysisColumn.TITLE.value: ["GPU update"],
            AnalysisColumn.CONTENT.value: ["GPU news"],
            AnalysisColumn.KEYWORDS.value: [pd.NA],
            AnalysisColumn.INFORMATION_CD.value: [CodeTable.INFORMATION_IT_INFO.value],
        }
    )
    mock_extract.return_value = ItKeywordResult(
        summary=" ",
        flow="release -> impact",
        interest_label="low",
        keywords=["GPU"],
    )

    analyze_it_keywords()

    mock_merge.assert_called_once()
    df = mock_merge.call_args[0][0]
    assert list(df.columns) == [
        AnalysisColumn.CRAWLING_ID.value,
        AnalysisColumn.KEYWORDS.value,
    ]
    assert df[AnalysisColumn.KEYWORDS.value].iloc[0] == "#GPU"


@patch("analyze_it_keywords.ThreadPoolExecutor")
@patch("analyze_it_keywords.merge_analysis_data")
@patch("analyze_it_keywords.extract_it_keywords")
@patch("analyze_it_keywords.get_it_keyword_target_data")
def test_pa_l3_itkw_014_parallel_workers_merge_success_rows(
    mock_get_targets: MagicMock,
    mock_extract: MagicMock,
    mock_merge: MagicMock,
    mock_executor: MagicMock,
) -> None:
    mock_get_targets.return_value = pd.DataFrame(
        {
            AnalysisColumn.CRAWLING_ID.value: [801, 802],
            AnalysisColumn.TITLE.value: ["A", "B"],
            AnalysisColumn.CONTENT.value: ["a", "b"],
            AnalysisColumn.KEYWORDS.value: [pd.NA, pd.NA],
            AnalysisColumn.INFORMATION_CD.value: [CodeTable.INFORMATION_IT_INFO.value] * 2,
        }
    )

    class InlineFuture:
        def __init__(self, value):
            self._value = value

        def result(self):
            return self._value

    class InlineExecutor:
        def __init__(self, max_workers):
            self.max_workers = max_workers

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def submit(self, fn, *args, **kwargs):
            return InlineFuture(fn(*args, **kwargs))

    mock_executor.side_effect = lambda max_workers: InlineExecutor(max_workers)
    mock_extract.side_effect = [
        ItKeywordResult(keywords=["A keyword"]),
        ItKeywordResult(keywords=["B keyword"]),
    ]

    analyze_it_keywords(max_rows=2, workers=2)

    mock_executor.assert_called_once_with(max_workers=2)
    assert mock_extract.call_count == 2
    mock_merge.assert_called_once()
    df = mock_merge.call_args[0][0]
    assert df[AnalysisColumn.CRAWLING_ID.value].tolist() == [801, 802]
    assert df[AnalysisColumn.KEYWORDS.value].tolist() == ["#A keyword", "#B keyword"]


@patch("analyze_it_keywords.merge_analysis_data")
@patch("analyze_it_keywords._ollama_chat_json")
@patch("analyze_it_keywords.preprocess_it_content")
@patch("analyze_it_keywords.get_it_keyword_target_data")
def test_pa_l3_itkw_008_preprocessing_failure_skips_ollama_and_merge(
    mock_get_targets: MagicMock,
    mock_preprocess: MagicMock,
    mock_ollama_chat_json: MagicMock,
    mock_merge: MagicMock,
) -> None:
    """전처리 검증 실패 row는 Ollama 호출과 MERGE 없이 skip한다."""
    mock_get_targets.return_value = pd.DataFrame(
        {
            AnalysisColumn.CRAWLING_ID.value: [501],
            AnalysisColumn.TITLE.value: ["AI 모델 업데이트"],
            AnalysisColumn.CONTENT.value: ["AI 모델 업데이트가 공개되었습니다."],
            AnalysisColumn.KEYWORDS.value: [pd.NA],
            AnalysisColumn.INFORMATION_CD.value: [CodeTable.INFORMATION_IT_INFO.value],
        }
    )
    mock_preprocess.side_effect = ValueError(
        "IC02 전처리 결과가 원문에 없는 문장을 포함했습니다."
    )

    analyze_it_keywords()

    mock_ollama_chat_json.assert_not_called()
    mock_merge.assert_not_called()


@patch("analyze_it_keywords.tqdm")
@patch("analyze_it_keywords.merge_analysis_data")
@patch("analyze_it_keywords.extract_it_keywords")
@patch("analyze_it_keywords.get_it_keyword_target_data")
def test_pa_l3_itkw_009_wraps_ic02_rows_with_progress_bar(
    mock_get_targets: MagicMock,
    mock_extract: MagicMock,
    mock_merge: MagicMock,
    mock_tqdm: MagicMock,
) -> None:
    """IC02 row 처리 루프는 tqdm 진행률 표시로 감싼다."""
    mock_get_targets.return_value = pd.DataFrame(
        {
            AnalysisColumn.CRAWLING_ID.value: [1, 2],
            AnalysisColumn.TITLE.value: ["A", "B"],
            AnalysisColumn.CONTENT.value: ["a", "b"],
            AnalysisColumn.KEYWORDS.value: [pd.NA, pd.NA],
            AnalysisColumn.INFORMATION_CD.value: [CodeTable.INFORMATION_IT_INFO.value] * 2,
        }
    )
    mock_extract.return_value = ItKeywordResult(keywords=["keyword"])
    mock_tqdm.side_effect = lambda iterable, **_kwargs: list(iterable)

    analyze_it_keywords(max_rows=2)

    mock_tqdm.assert_called_once()
    assert mock_tqdm.call_args.kwargs["total"] == 2
    assert mock_tqdm.call_args.kwargs["desc"] == AnalyzeItKeywordsConfig.PROGRESS_DESC
    assert mock_tqdm.call_args.kwargs["unit"] == AnalyzeItKeywordsConfig.PROGRESS_UNIT
    assert mock_extract.call_count == 2
    mock_merge.assert_called_once()


@patch("analyze_it_keywords.merge_analysis_data")
@patch("analyze_it_keywords._ollama_chat_json")
@patch("analyze_it_keywords.get_it_keyword_target_data")
def test_pa_l3_itkw_010_invalid_candidate_keywords_skip_merge(
    mock_get_targets: MagicMock,
    mock_chat: MagicMock,
    mock_merge: MagicMock,
) -> None:
    """후보군 밖 키워드만 반환된 row는 빈 결과로 보고 MERGE하지 않는다."""
    mock_get_targets.return_value = pd.DataFrame(
        {
            AnalysisColumn.CRAWLING_ID.value: [901],
            AnalysisColumn.TITLE.value: ["git-sync 리모트 미러링"],
            AnalysisColumn.CONTENT.value: [
                "소스 리모트에서 타겟 리모트로 ref와 오브젝트를 직접 스트리밍합니다."
            ],
            AnalysisColumn.KEYWORDS.value: [pd.NA],
            AnalysisColumn.INFORMATION_CD.value: [CodeTable.INFORMATION_IT_INFO.value],
        }
    )
    mock_chat.return_value = {
        "summary": "요약",
        "flow": "흐름",
        "interest_label": "low",
        "keywords": ["Git 레미트리치닝", "프로덕션 배포"],
    }

    analyze_it_keywords()

    mock_merge.assert_not_called()
