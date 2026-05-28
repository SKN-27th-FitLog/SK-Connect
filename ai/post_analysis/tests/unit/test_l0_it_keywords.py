"""PA-L0-ITKW: IC02 IT keyword pure helpers and config."""

import pytest
import pandas as pd

from analyze_it_keywords import (
    ItKeywordResult,
    build_it_keyword_prompt,
    compress_it_content,
    compute_interest_signal,
    get_it_keyword_int_config,
    get_ollama_base_url,
    get_ollama_model_name,
    normalize_it_content,
    normalize_it_keywords,
    preprocess_it_content,
    split_content_units,
    validate_preprocessed_content,
)
from common.constant import AnalyzeItKeywordsConfig
from common.errors import PostAnalysisErrors


def test_pa_l0_itkw_001_config_defaults() -> None:
    """PA-L0-ITKW-001 [불변]: IC02 키워드 기본 모델과 관심도 기준."""
    assert AnalyzeItKeywordsConfig.DEFAULT_MODEL == "gemma4:26b"
    assert AnalyzeItKeywordsConfig.MODEL_ENV_KEY == "POST_ANALYSIS_IT_KEYWORDS_MODEL"
    assert AnalyzeItKeywordsConfig.OLLAMA_BASE_URL_ENV_KEY == "OLLAMA_BASE_URL"
    assert AnalyzeItKeywordsConfig.MAX_KEYWORDS == 7
    assert AnalyzeItKeywordsConfig.INTEREST_HIGH_THRESHOLD == 1000
    assert AnalyzeItKeywordsConfig.INTEREST_MEDIUM_THRESHOLD == 100


def test_pa_l0_itkw_002_error_messages() -> None:
    """PA-L0-ITKW-002 [정상]: IC02 키워드 오류 메시지가 독립 namespace에 있다."""
    assert "IT 키워드" in PostAnalysisErrors.ItKeywords.missing_columns(["title"])
    assert "처리할" in PostAnalysisErrors.ItKeywords.no_pending_rows()
    assert "crawling_id" in PostAnalysisErrors.ItKeywords.row_processing_failed()


def test_pa_l0_itkw_003_normalize_keywords_list() -> None:
    """PA-L0-ITKW-003 [정상]: list 키워드를 # 구분 문자열로 정규화한다."""
    assert normalize_it_keywords([" PyTorch ", "PyTorch", "", "#GPU 비용"]) == "#PyTorch#GPU 비용"


def test_pa_l0_itkw_004_normalize_keywords_string() -> None:
    """PA-L0-ITKW-004 [정상]: 기존 # 문자열도 중복 제거한다."""
    assert normalize_it_keywords("#PyTorch# GPU 비용 #PyTorch") == "#PyTorch#GPU 비용"


def test_pa_l0_itkw_005_interest_signal_high_medium_low() -> None:
    """PA-L0-ITKW-005 [정상]: view/comment/point 기반 관심도 등급."""
    high = compute_interest_signal({"view_count": 800, "comment_count": 10, "point": 5})
    medium = compute_interest_signal({"view_count": 80, "comment_count": 2, "point": 0})
    low = compute_interest_signal({"view_count": None, "comment_count": pd.NA, "point": -3})
    assert high["level"] == "high"
    assert high["score"] == 1000
    assert medium["level"] == "medium"
    assert low["level"] == "low"
    assert low["score"] == 0


def test_pa_l0_itkw_006_prompt_contains_summary_flow_interest() -> None:
    """PA-L0-ITKW-006 [정상]: 프롬프트에 요약·흐름·관심도 요구가 포함된다."""
    prompt = build_it_keyword_prompt(
        {
            "title": "PyTorch 2.5 릴리스",
            "content": "추론 성능과 배포 편의성이 개선되었습니다.",
            "view_count": 1200,
            "comment_count": 8,
            "point": 3,
        }
    )
    assert "summary" in prompt
    assert "flow" in prompt
    assert "interest_label" in prompt
    assert "keywords" in prompt
    assert "PyTorch 2.5 릴리스" in prompt


def test_pa_l0_itkw_006_1_prompt_handles_missing_title() -> None:
    """PA-L0-ITKW-006-1 [경계]: title 결측이어도 content 기반 프롬프트를 만든다."""
    prompt = build_it_keyword_prompt(
        {
            "title": pd.NA,
            "content": "GPU 배포 비용이 줄었습니다.",
        }
    )
    assert "GPU 배포 비용" in prompt


def test_pa_l0_itkw_007_ollama_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """PA-L0-ITKW-007 [정상]: Ollama 모델과 base URL은 환경변수로 바꿀 수 있다."""
    monkeypatch.setenv("POST_ANALYSIS_IT_KEYWORDS_MODEL", "gemma4:e4b")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/")
    assert get_ollama_model_name() == "gemma4:e4b"
    assert get_ollama_base_url() == "http://127.0.0.1:11434"


def test_pa_l0_itkw_008_response_model() -> None:
    """PA-L0-ITKW-008 [정상]: LLM 응답 모델은 summary/flow/interest_label/keywords를 가진다."""
    result = ItKeywordResult(
        summary="릴리스 요약",
        flow="발표 -> 영향",
        interest_label="high",
        keywords=["PyTorch", "추론 성능"],
    )
    assert result.keywords == ["PyTorch", "추론 성능"]


def test_pa_l0_itkw_009_preprocessing_config_defaults() -> None:
    """PA-L0-ITKW-009 [불변]: IC02 전처리 기본 정책값은 config에 모인다."""
    assert AnalyzeItKeywordsConfig.MAX_CONTENT_CHARS_ENV_KEY == (
        "POST_ANALYSIS_IT_KEYWORDS_MAX_CONTENT_CHARS"
    )
    assert AnalyzeItKeywordsConfig.MAX_CONTENT_UNITS_ENV_KEY == (
        "POST_ANALYSIS_IT_KEYWORDS_MAX_CONTENT_UNITS"
    )
    assert AnalyzeItKeywordsConfig.MAX_UNIT_CHARS_ENV_KEY == (
        "POST_ANALYSIS_IT_KEYWORDS_MAX_UNIT_CHARS"
    )
    assert AnalyzeItKeywordsConfig.REQUEST_TIMEOUT_SECONDS_ENV_KEY == (
        "POST_ANALYSIS_IT_KEYWORDS_TIMEOUT_SECONDS"
    )
    assert AnalyzeItKeywordsConfig.MAX_CONTENT_CHARS == 2500
    assert AnalyzeItKeywordsConfig.MAX_CONTENT_UNITS == 8
    assert AnalyzeItKeywordsConfig.MAX_UNIT_CHARS == 1200
    assert AnalyzeItKeywordsConfig.COMPRESSED_CONTENT_PROMPT_LABEL == "[compressed_content]"
    assert "summary" in AnalyzeItKeywordsConfig.RESPONSE_SCHEMA_EXAMPLE
    assert "AI" in AnalyzeItKeywordsConfig.IMPORTANT_TERMS


def test_pa_l0_itkw_010_int_config_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """PA-L0-ITKW-010 [정상]: IC02 정수 설정은 환경변수로 override된다."""
    monkeypatch.setenv(AnalyzeItKeywordsConfig.MAX_CONTENT_CHARS_ENV_KEY, "600")

    assert (
        get_it_keyword_int_config(
            AnalyzeItKeywordsConfig.MAX_CONTENT_CHARS_ENV_KEY,
            AnalyzeItKeywordsConfig.MAX_CONTENT_CHARS,
        )
        == 600
    )


def test_pa_l0_itkw_011_int_config_falls_back_for_invalid_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PA-L0-ITKW-011 [경계]: 잘못된 정수 env 값은 배치를 중단하지 않고 기본값을 쓴다."""
    monkeypatch.setenv(AnalyzeItKeywordsConfig.MAX_CONTENT_UNITS_ENV_KEY, "not-number")
    assert (
        get_it_keyword_int_config(
            AnalyzeItKeywordsConfig.MAX_CONTENT_UNITS_ENV_KEY,
            AnalyzeItKeywordsConfig.MAX_CONTENT_UNITS,
        )
        == AnalyzeItKeywordsConfig.MAX_CONTENT_UNITS
    )

    monkeypatch.setenv(AnalyzeItKeywordsConfig.MAX_CONTENT_UNITS_ENV_KEY, "0")
    assert (
        get_it_keyword_int_config(
            AnalyzeItKeywordsConfig.MAX_CONTENT_UNITS_ENV_KEY,
            AnalyzeItKeywordsConfig.MAX_CONTENT_UNITS,
        )
        == AnalyzeItKeywordsConfig.MAX_CONTENT_UNITS
    )


def test_pa_l0_itkw_012_short_content_keeps_normalized_original() -> None:
    """PA-L0-ITKW-012 [정상]: 짧은 원문은 내용 압축 없이 정규화 결과를 그대로 둔다."""
    original = "첫 줄&nbsp;내용\r\n\r\n다음 줄  내용"

    compressed = compress_it_content("AI 릴리스", original)

    assert compressed == "첫 줄 내용\n\n다음 줄 내용"


def test_pa_l0_itkw_012_1_short_content_keeps_original_even_with_many_units(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PA-L0-ITKW-012-1 [경계]: 짧은 원문은 unit 수가 많아도 원문 정규화 결과를 유지한다."""
    monkeypatch.setenv(AnalyzeItKeywordsConfig.MAX_CONTENT_UNITS_ENV_KEY, "2")
    original = "\n\n".join(
        [
            "AI 모델 업데이트가 공개됐습니다.",
            "GPU 배포 영향이 언급됐습니다.",
            "API 변경 사항이 정리됐습니다.",
        ]
    )

    compressed = compress_it_content("AI 업데이트", original)

    assert compressed == normalize_it_content(original)


def test_pa_l0_itkw_013_long_content_is_compressed_under_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PA-L0-ITKW-013 [정상]: 긴 원문은 max chars 이하의 원문 발췌문으로 압축한다."""
    monkeypatch.setenv(AnalyzeItKeywordsConfig.MAX_CONTENT_CHARS_ENV_KEY, "120")
    monkeypatch.setenv(AnalyzeItKeywordsConfig.MAX_CONTENT_UNITS_ENV_KEY, "3")
    long_content = "\n\n".join(
        [
            "AI 모델 업데이트가 공개됐고 추론 성능 개선이 핵심입니다.",
            "행사와 주변 소식과 일정 안내입니다.",
            "GPU 비용과 배포 자동화 영향은 개발자에게 중요합니다.",
            "커뮤니티 평가는 API 변경과 라이선스 리스크를 주로 언급합니다.",
            "마지막으로 보안 취약점 대응 일정이 정리됐습니다.",
        ]
    )

    compressed = compress_it_content("AI 모델 업데이트", long_content)

    assert len(compressed) <= 120
    assert len(compressed) < len(normalize_it_content(long_content))
    validate_preprocessed_content(
        normalize_it_content(long_content),
        compressed,
        120,
    )


def test_pa_l0_itkw_014_validation_rejects_text_not_in_original() -> None:
    """PA-L0-ITKW-014 [실패]: 압축 결과가 원문 밖 문장을 포함하면 검증 실패."""
    original = normalize_it_content("AI 모델 업데이트가 공개됐습니다.")
    compressed = "원문에 없는 투자 조언입니다."

    with pytest.raises(ValueError, match="원문"):
        validate_preprocessed_content(original, compressed, 100)


def test_pa_l0_itkw_015_validation_rejects_uncompressed_long_content() -> None:
    """PA-L0-ITKW-015 [실패]: 긴 원문이 실제로 줄지 않았으면 검증 실패."""
    original = normalize_it_content(
        "AI 모델 업데이트가 공개됐습니다.\n\nGPU 배포 영향이 큽니다."
    )

    with pytest.raises(ValueError, match="압축"):
        validate_preprocessed_content(original, original, 20)


def test_pa_l0_itkw_016_long_paragraph_splits_by_sentence() -> None:
    """PA-L0-ITKW-016 [경계]: 긴 단일 문단은 문장 단위 후보로 분리한다."""
    paragraph = (
        "AI 모델 업데이트가 공개됐습니다. "
        "추론 성능 개선이 핵심입니다. "
        "GPU 비용과 배포 자동화 영향은 개발자에게 중요합니다."
    )

    units = split_content_units(paragraph, 35)

    assert len(units) >= 2
    assert "추론 성능 개선이 핵심입니다." in units


def test_pa_l0_itkw_017_preprocess_row_uses_env_limits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PA-L0-ITKW-017 [정상]: row 전처리는 env 제한값을 적용한다."""
    monkeypatch.setenv(AnalyzeItKeywordsConfig.MAX_CONTENT_CHARS_ENV_KEY, "80")
    row = {
        "title": "GPU 배포",
        "content": (
            "GPU 배포 자동화가 공개됐습니다.\n\n"
            "행사 안내 문단입니다.\n\n"
            "API 변경과 보안 리스크가 함께 언급됐습니다."
        ),
    }

    compressed = preprocess_it_content(row)

    assert len(compressed) <= 80
    assert "GPU 배포 자동화" in compressed
