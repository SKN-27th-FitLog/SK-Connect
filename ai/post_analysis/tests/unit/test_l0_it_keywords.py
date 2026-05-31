"""PA-L0-ITKW: IC02 IT keyword pure helpers and config."""

import json
from unittest.mock import MagicMock, patch

import pytest
import pandas as pd

from analyze_it_keywords import (
    ItKeywordResult,
    _ollama_chat_json,
    build_summary_enriched_content,
    build_it_keyword_prompt,
    compress_it_content,
    compute_interest_signal,
    extract_it_keywords,
    extract_original_content,
    get_it_keyword_int_config,
    get_ollama_base_url,
    get_ollama_model_name,
    normalize_it_content,
    normalize_it_keywords,
    preprocess_it_content,
    select_content_units,
    split_content_units,
    validate_preprocessed_content,
)
from common.constant import AnalyzeItKeywordsConfig
from common.errors import PostAnalysisErrors
from common.it_keyword_candidates import (
    ItKeywordCandidate,
    extract_it_keyword_candidates,
    filter_it_keywords_by_candidates,
    format_candidate_keywords_for_prompt,
)


def test_pa_l0_itkw_001_config_defaults() -> None:
    """PA-L0-ITKW-001 [불변]: IC02 키워드 기본 모델과 관심도 기준."""
    assert AnalyzeItKeywordsConfig.DEFAULT_MODEL == "gemma4:e4b"
    assert AnalyzeItKeywordsConfig.MODEL_ENV_KEY == "POST_ANALYSIS_IT_KEYWORDS_MODEL"
    assert AnalyzeItKeywordsConfig.OLLAMA_BASE_URL_ENV_KEY == "OLLAMA_BASE_URL"
    assert AnalyzeItKeywordsConfig.MIN_KEYWORDS == 12
    assert AnalyzeItKeywordsConfig.MAX_KEYWORDS == 15
    assert AnalyzeItKeywordsConfig.REQUEST_TIMEOUT_SECONDS == 300
    assert AnalyzeItKeywordsConfig.INTEREST_HIGH_THRESHOLD == 1000
    assert AnalyzeItKeywordsConfig.INTEREST_MEDIUM_THRESHOLD == 100
    assert AnalyzeItKeywordsConfig.CANDIDATE_PROMPT_LABEL == "[candidate_keywords]"
    assert AnalyzeItKeywordsConfig.MAX_PROMPT_CANDIDATES == 40
    assert AnalyzeItKeywordsConfig.MIN_CANDIDATE_SCORE > 0


def test_pa_l0_itkw_002_error_messages() -> None:
    """PA-L0-ITKW-002 [정상]: IC02 키워드 오류 메시지가 독립 namespace에 있다."""
    assert "IT 키워드" in PostAnalysisErrors.ItKeywords.missing_columns(["title"])
    assert "처리할" in PostAnalysisErrors.ItKeywords.no_pending_rows()
    assert "crawling_id" in PostAnalysisErrors.ItKeywords.row_processing_failed()


def test_pa_l0_itkw_003_normalize_keywords_list() -> None:
    """PA-L0-ITKW-003 [정상]: list 키워드를 # 구분 문자열로 정규화한다."""
    assert normalize_it_keywords([" PyTorch ", "PyTorch", "", "#GPU 비용"]) == "#PyTorch#GPU 비용"


def test_pa_l0_itkw_003_1_normalize_keywords_keeps_up_to_config_limit() -> None:
    """PA-L0-ITKW-003-1 [정상]: IC02 키워드는 원문 흐름 보존을 위해 최대 15개까지 유지한다."""
    keywords = [f"keyword-{index}" for index in range(1, 17)]

    normalized = normalize_it_keywords(keywords)

    assert normalized.count("#") == AnalyzeItKeywordsConfig.MAX_KEYWORDS
    assert "#keyword-15" in normalized
    assert "#keyword-16" not in normalized


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
    assert "- keywords는 12개 이상 15개 이하입니다." in prompt


def test_pa_l0_itkw_006_1_prompt_handles_missing_title() -> None:
    """PA-L0-ITKW-006-1 [경계]: title 결측이어도 content 기반 프롬프트를 만든다."""
    prompt = build_it_keyword_prompt(
        {
            "title": pd.NA,
            "content": "GPU 배포 비용이 줄었습니다.",
        }
    )
    assert "GPU 배포 비용" in prompt


def test_pa_l0_itkw_006_2_prompt_guides_summary_for_post_generation() -> None:
    """PA-L0-ITKW-006-2 [정상]: summary는 게시글 생성용 판단 재료를 포함하도록 지시한다."""
    prompt = build_it_keyword_prompt(
        {
            "title": "RustFS S3 호환 객체 스토리지",
            "content": "RustFS는 Apache 2.0 라이선스와 S3 호환 API를 제공하며 일부 기능은 Under Testing입니다.",
        },
        candidates=[
            ItKeywordCandidate("RustFS", 10, "title", 2),
            ItKeywordCandidate("S3 호환 API", 9, "content", 1),
            ItKeywordCandidate("Apache 2.0", 8, "content", 1),
        ],
    )

    assert "게시글 생성의 기반" in prompt
    assert "차별점" in prompt
    assert "실무 포인트" in prompt
    assert "제한사항" in prompt
    assert "원문에 없는 장점" in prompt


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


def test_pa_l0_itkw_008_1_response_schema_example_matches_keyword_target() -> None:
    """PA-L0-ITKW-008-1 [정상]: 프롬프트 예시도 12개 이상 키워드 목표를 보여준다."""
    example = json.loads(AnalyzeItKeywordsConfig.RESPONSE_SCHEMA_EXAMPLE)

    assert len(example["keywords"]) >= AnalyzeItKeywordsConfig.MIN_KEYWORDS
    assert len(example["keywords"]) <= AnalyzeItKeywordsConfig.MAX_KEYWORDS


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
    assert AnalyzeItKeywordsConfig.PROMPT_SCHEMA_HEADER == "반환 JSON 스키마:"
    assert AnalyzeItKeywordsConfig.PROMPT_CONSTRAINTS_HEADER == "제약:"
    assert AnalyzeItKeywordsConfig.PROMPT_KEYWORD_COUNT_TEMPLATE == (
        "- keywords는 {min_keywords}개 이상 {max_keywords}개 이하입니다."
    )
    assert AnalyzeItKeywordsConfig.PROMPT_KEYWORD_GUIDE == (
        "- keywords에는 기술명, 제품명, 프레임워크, 변경점, 영향, 리스크, 활용 포인트, 독자 관점을 균형 있게 넣습니다."
    )
    assert "후보군" in AnalyzeItKeywordsConfig.PROMPT_CANDIDATE_LIMIT_GUIDE
    assert "이해" in AnalyzeItKeywordsConfig.CANDIDATE_STOPWORDS
    assert "NNG" in AnalyzeItKeywordsConfig.CANDIDATE_NOUN_POS_TAGS
    assert "VA" in AnalyzeItKeywordsConfig.CANDIDATE_SIGNAL_POS_TAGS


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


def test_pa_l0_itkw_018_prompt_uses_compressed_content_label(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PA-L0-ITKW-018 [정상]: prompt는 원문 전체가 아니라 검증된 compressed_content를 쓴다."""
    monkeypatch.setenv(AnalyzeItKeywordsConfig.MAX_CONTENT_CHARS_ENV_KEY, "120")
    raw_content = (
        "AI 모델 업데이트가 공개됐고 추론 성능 개선을 설명합니다.\n\n"
        "행사 안내는 현장 분위기를 설명하는 긴 문단이며 참석자 동선과 부스 배치 안내를 "
        "자세히 반복하고 발표장 조명과 등록 절차까지 길게 덧붙이며 후원사 소개도 이어집니다.\n\n"
        "GPU 비용과 API 변경 영향은 개발자에게 중요합니다."
    )
    assert len(normalize_it_content(raw_content)) > 120

    prompt = build_it_keyword_prompt(
        {
            "title": "AI 모델 업데이트",
            "content": raw_content,
            "view_count": 100,
            "comment_count": 1,
            "point": 0,
        }
    )

    assert AnalyzeItKeywordsConfig.COMPRESSED_CONTENT_PROMPT_LABEL in prompt
    assert AnalyzeItKeywordsConfig.CONTENT_PROMPT_LABEL not in prompt
    assert raw_content not in prompt
    assert "행사 안내는 현장 분위기" not in prompt


@patch("analyze_it_keywords.urllib.request.urlopen")
def test_pa_l0_itkw_019_ollama_timeout_uses_env_override(
    mock_urlopen: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PA-L0-ITKW-019 [정상]: Ollama timeout은 IC02 전용 env override를 따른다."""

    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
            return None

        def read(self) -> bytes:
            return (
                b'{"message":{"content":"{'
                b'\\"summary\\":\\"s\\",'
                b'\\"flow\\":\\"f\\",'
                b'\\"interest_label\\":\\"low\\",'
                b'\\"keywords\\":[\\"AI\\"]'
                b'}"}}'
            )

    monkeypatch.setenv(AnalyzeItKeywordsConfig.REQUEST_TIMEOUT_SECONDS_ENV_KEY, "45")
    mock_urlopen.return_value = FakeResponse()

    _ollama_chat_json("prompt")

    assert mock_urlopen.call_args.kwargs["timeout"] == 45


def test_pa_l0_itkw_020_selection_keeps_searching_after_oversized_ranked_unit() -> None:
    """PA-L0-ITKW-020 [경계]: 상위 후보가 너무 길면 예산 안에 드는 다음 후보를 선택한다."""
    units = [
        "AI GPU 모델 업데이트와 배포 자동화 영향이 길게 설명되어 글자 수 예산을 초과합니다.",
        "일정 안내",
        "API 변경",
    ]

    selected = select_content_units(
        "AI GPU",
        units,
        max_chars=10,
        max_units=1,
    )

    assert selected == ["API 변경"]


def test_pa_l0_itkw_021_candidate_extraction_keeps_source_terms() -> None:
    """PA-L0-ITKW-021 [정상]: 후보 추출은 원문에 실제 등장한 기술 표현을 유지한다."""
    candidates = extract_it_keyword_candidates(
        "git-sync 리모트 미러링",
        "로컬 체크아웃 없이 소스 리모트에서 타겟 리모트로 ref와 오브젝트를 직접 스트리밍합니다. "
        "메모리 사용량은 일정합니다.",
    )

    texts = [candidate.text for candidate in candidates]

    assert "git-sync" in texts
    assert "소스 리모트" in texts
    assert "타겟 리모트" in texts
    assert "메모리 사용량" in texts


def test_pa_l0_itkw_022_candidate_filter_rejects_generated_composites() -> None:
    """PA-L0-ITKW-022 [정상]: 원문 후보군 밖 LLM 조합어는 저장 후보에서 제거한다."""
    candidates = extract_it_keyword_candidates(
        "git-sync 리모트 미러링",
        "소스 리모트에서 타겟 리모트로 ref와 오브젝트를 직접 스트리밍하며 메모리 사용량은 일정합니다.",
    )

    filtered = filter_it_keywords_by_candidates(
        [
            "git-sync",
            "타겟 리모트",
            "Git 레미트리치닝",
            "타겟 리먼트 관리",
            "프로덕션 배포",
        ],
        candidates,
    )

    assert filtered == ["git-sync", "타겟 리모트"]


def test_pa_l0_itkw_023_candidate_filter_rejects_low_quality_words() -> None:
    """PA-L0-ITKW-023 [정상]: 저품질 일반어와 깨진 조합어를 제거한다."""
    candidates = extract_it_keyword_candidates(
        "ZFS 튜닝",
        "무작위 접근 워크로드에서는 recordsize와 ARC 메모리 캐시, IO 병합을 함께 검토합니다.",
    )

    filtered = filter_it_keywords_by_candidates(
        ["ZFS", "recordsize", "박스크립트 시스템", "이해 필요", "ARC 메모리 캐시"],
        candidates,
    )

    assert filtered == ["ZFS", "recordsize", "ARC 메모리 캐시"]


def test_pa_l0_itkw_024_candidate_prompt_format_is_ranked_and_limited() -> None:
    """PA-L0-ITKW-024 [정상]: prompt 후보군은 점수 순으로 제한된 줄 수만 제공한다."""
    candidates = extract_it_keyword_candidates(
        "NVIDIA Agent Skills",
        "NVIDIA Agent Skills는 CUDA-X 라이브러리와 SkillSpector 검증 파이프라인을 제공합니다.",
    )

    prompt_text = format_candidate_keywords_for_prompt(candidates, limit=3)

    assert prompt_text.count("\n") <= 2
    assert "NVIDIA Agent Skills" in prompt_text


def test_pa_l0_itkw_025_prompt_includes_candidate_keywords() -> None:
    """PA-L0-ITKW-025 [정상]: IC02 prompt는 원문 후보군과 후보군 제한 규칙을 포함한다."""
    prompt = build_it_keyword_prompt(
        {
            "title": "NVIDIA Agent Skills",
            "content": "NVIDIA Agent Skills는 CUDA-X 라이브러리와 SkillSpector 검증 파이프라인을 제공합니다.",
        }
    )

    assert AnalyzeItKeywordsConfig.CANDIDATE_PROMPT_LABEL in prompt
    assert "후보군 밖 새 키워드" in prompt
    assert "NVIDIA Agent Skills" in prompt


@patch("analyze_it_keywords._ollama_chat_json")
def test_pa_l0_itkw_026_extract_filters_llm_keywords_by_candidates(
    mock_chat: MagicMock,
) -> None:
    """PA-L0-ITKW-026 [정상]: LLM 응답은 저장 전 원문 후보군으로 다시 제한된다."""
    mock_chat.return_value = {
        "summary": "git-sync 요약",
        "flow": "동기화 -> 메모리 영향",
        "interest_label": "medium",
        "keywords": ["git-sync", "타겟 리모트", "Git 레미트리치닝", "프로덕션 배포"],
    }

    result = extract_it_keywords(
        {
            "title": "git-sync 리모트 미러링",
            "content": "소스 리모트에서 타겟 리모트로 ref와 오브젝트를 직접 스트리밍하며 메모리 사용량은 일정합니다.",
        }
    )

    assert result.keywords == ["git-sync", "타겟 리모트"]


def test_pa_l0_itkw_028_build_summary_enriched_content_formats_body_and_summary() -> None:
    """PA-L0-ITKW-028 [정상]: IC02 본문과 요약을 content 저장 포맷으로 합친다."""
    enriched = build_summary_enriched_content(
        "PyTorch 2.5 release\n\nInference speed improved.",
        "PyTorch 2.5가 추론 속도를 개선했다.",
    )

    assert enriched == (
        "[본문]\n"
        "PyTorch 2.5 release\n\nInference speed improved.\n\n"
        "[요약]\n"
        "PyTorch 2.5가 추론 속도를 개선했다."
    )


def test_pa_l0_itkw_029_build_summary_enriched_content_deduplicates_existing_summary() -> None:
    """PA-L0-ITKW-029 [정상]: 이미 저장 포맷인 content는 원문만 다시 사용한다."""
    content = "[본문]\nOriginal body\n\n[요약]\nOld summary"

    enriched = build_summary_enriched_content(content, "New summary")

    assert enriched == "[본문]\nOriginal body\n\n[요약]\nNew summary"
    assert extract_original_content(content) == "Original body"


def test_pa_l0_itkw_030_build_summary_enriched_content_skips_blank_summary() -> None:
    """PA-L0-ITKW-030 [경계]: 요약이 비어 있으면 content 업데이트 값을 만들지 않는다."""
    assert build_summary_enriched_content("Original body", "  ") is None


def test_pa_l0_itkw_027_candidate_extraction_rejects_attached_prefix_fragment() -> None:
    """PA-L0-ITKW-027 [정상]: 접두사가 잘린 어색한 부분 후보는 prompt 후보군에서 제외한다."""
    candidates = extract_it_keyword_candidates(
        "ZFS 튜닝",
        "무작위 접근 워크로드에서는 recordsize와 ARC 메모리 캐시, IO 병합을 함께 검토합니다.",
    )

    texts = [candidate.text for candidate in candidates]

    assert "작위" not in texts
    assert "작위 접근" not in texts
    assert "작위 접근 워크" not in texts
    assert "접근 워크" not in texts
    assert "로드" not in texts
    assert "접근 워크로드" in texts
