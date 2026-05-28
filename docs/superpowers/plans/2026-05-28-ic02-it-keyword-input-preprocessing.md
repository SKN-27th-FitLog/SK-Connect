# IC02 IT Keyword Input Preprocessing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** IC02 IT 뉴스 키워드 추출에서 Ollama 호출 전 원문 기반 압축 전처리와 검증을 추가해 긴 본문으로 인한 timeout 위험을 줄인다.

**Architecture:** 기존 IC01 맛집 감성/BERT 키워드 흐름은 변경하지 않는다. `analyze_it_keywords.py` 안에 IC02 전용 순수 전처리 헬퍼를 추가하고, 숫자 제한값, prompt 라벨, prompt 지시문, IT scoring 용어는 `AnalyzeItKeywordsConfig`에 모은다. 검증 실패 row는 기존 row 단위 예외 처리 흐름으로 skip되어 LLM 호출과 DB merge 대상에서 제외된다.

**Tech Stack:** Python, pandas, pydantic, urllib stdlib Ollama HTTP API, pytest, existing `post_analysis` PostgreSQL helpers.

---

## Scope Guard

수정 허용 범위:

- Modify: `ai/post_analysis/common/constant.py`
- Modify: `ai/post_analysis/analyze_it_keywords.py`
- Modify: `ai/post_analysis/tests/unit/test_l0_it_keywords.py`
- Modify: `ai/post_analysis/tests/unit/test_l3_analyze_it_keywords_indirect.py`

수정 금지 범위:

- `ai/post_analysis/get_reviews.py`
- `ai/post_analysis/analyze_sentimental.py`
- `ai/post_analysis/analyze_keywords.py`
- `ai/post_analysis/pipeline.py`
- `ai/post_analysis/postgresql`
- `etl/meal`
- `etl/it_news`
- `ai/postmake_pipeline`
- DB schema files

## File Responsibilities

- `common/constant.py`: IC02 전처리 제한값, env key, prompt 라벨, prompt 지시문, response schema 예시, IT 중요 용어, 정규화 패턴 문자열을 보관한다.
- `analyze_it_keywords.py`: IC02 row의 content를 정규화, unit 분리, deterministic 선택, 재조립, 검증한 뒤 prompt를 생성한다. Ollama timeout은 env override를 읽는다.
- `test_l0_it_keywords.py`: 설정값, env override, 순수 전처리 헬퍼, prompt 입력 형태를 검증한다.
- `test_l3_analyze_it_keywords_indirect.py`: 전처리 검증 실패 row가 LLM 호출과 DB merge에서 제외되는지 검증한다.

## Global And Hardcoding Rule

- 새 mutable global state를 만들지 않는다.
- module-level cache, accumulator, singleton state가 필요해지는 경우 구현을 멈추고 사용자 확인을 받는다.
- 새 고정 문자열, 숫자 제한값, prompt 문구, env key, scoring 용어는 `AnalyzeItKeywordsConfig`에 둔다.
- 불변 class constant는 허용한다. 이는 기존 `AnalyzeItKeywordsConfig` 패턴과 동일한 설정 저장 방식이다.
- 전처리 함수 내부의 숫자 literal은 인덱스 비교처럼 Python 제어 흐름상 의미가 명확한 값만 사용하고, 정책값은 config에서 읽는다.

---

### Task 1: Add Config And Env Helper Contracts

**Files:**
- Modify: `ai/post_analysis/common/constant.py`
- Modify: `ai/post_analysis/analyze_it_keywords.py`
- Test: `ai/post_analysis/tests/unit/test_l0_it_keywords.py`

- [ ] **Step 1: Write failing config tests**

Append these tests to `ai/post_analysis/tests/unit/test_l0_it_keywords.py`:

```python
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
```

Add `get_it_keyword_int_config` to the existing import block in that test file:

```python
from analyze_it_keywords import (
    ItKeywordResult,
    build_it_keyword_prompt,
    compute_interest_signal,
    get_it_keyword_int_config,
    get_ollama_base_url,
    get_ollama_model_name,
    normalize_it_keywords,
)
```

- [ ] **Step 2: Run config tests and verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest ai\post_analysis\tests\unit\test_l0_it_keywords.py::test_pa_l0_itkw_009_preprocessing_config_defaults ai\post_analysis\tests\unit\test_l0_it_keywords.py::test_pa_l0_itkw_010_int_config_env_override ai\post_analysis\tests\unit\test_l0_it_keywords.py::test_pa_l0_itkw_011_int_config_falls_back_for_invalid_values -v
```

Expected: FAIL because the new config constants and `get_it_keyword_int_config` are not implemented.

- [ ] **Step 3: Add config constants**

Modify `AnalyzeItKeywordsConfig` in `ai/post_analysis/common/constant.py` by adding these attributes inside the class:

```python
    REQUEST_TIMEOUT_SECONDS_ENV_KEY = "POST_ANALYSIS_IT_KEYWORDS_TIMEOUT_SECONDS"
    MAX_CONTENT_CHARS_ENV_KEY = "POST_ANALYSIS_IT_KEYWORDS_MAX_CONTENT_CHARS"
    MAX_CONTENT_UNITS_ENV_KEY = "POST_ANALYSIS_IT_KEYWORDS_MAX_CONTENT_UNITS"
    MAX_UNIT_CHARS_ENV_KEY = "POST_ANALYSIS_IT_KEYWORDS_MAX_UNIT_CHARS"
    MAX_CONTENT_CHARS = 2500
    MAX_CONTENT_UNITS = 8
    MAX_UNIT_CHARS = 1200
    MIN_POSITIVE_CONFIG_VALUE = 1
    TITLE_PROMPT_LABEL = "[title]"
    CONTENT_PROMPT_LABEL = "[content]"
    COMPRESSED_CONTENT_PROMPT_LABEL = "[compressed_content]"
    INTEREST_PROMPT_LABEL = "[interest]"
    NORMALIZED_PARAGRAPH_SEPARATOR = "\n\n"
    PARAGRAPH_SPLIT_PATTERN = r"\n\s*\n+"
    LINE_BREAK_PATTERN = r"\r\n|\r"
    MULTI_BLANK_LINE_PATTERN = r"\n{3,}"
    INLINE_SPACE_PATTERN = r"[ \t\f\v]+"
    SENTENCE_SPLIT_PATTERN = r"(?<=[.!?。！？다요음함됨임])\s+|\n+"
    NUMBER_PATTERN = r"\d"
    WORD_PATTERN = r"[0-9A-Za-z가-힣]+"
    IMPORTANT_TERMS = (
        "AI",
        "LLM",
        "모델",
        "추론",
        "학습",
        "배포",
        "GPU",
        "CPU",
        "성능",
        "비용",
        "보안",
        "취약점",
        "릴리스",
        "버전",
        "업데이트",
        "프레임워크",
        "API",
        "오픈소스",
        "라이선스",
        "데이터",
        "개발자",
        "에이전트",
        "자동화",
        "클라우드",
        "인프라",
        "영향",
        "리스크",
        "사용",
    )
    PROMPT_INSTRUCTIONS = (
        "당신은 IT 뉴스 게시글 기획을 위한 키워드 분석기입니다.",
        "입력 글을 읽고 요약, 글의 흐름, 관심도 라벨, 게시글 생성용 키워드를 JSON으로만 반환하세요.",
        "입력 본문은 원문에서 발췌해 압축한 compressed_content입니다.",
        "키워드는 기술 주제와 게시글 독자 관점을 함께 포함해야 합니다.",
        "원문에 없는 인물, 사실, 제품명을 만들지 않습니다.",
        "JSON 외 텍스트를 출력하지 않습니다.",
    )
    RESPONSE_SCHEMA_EXAMPLE = (
        '{"summary":"릴리스 핵심 요약","flow":"발표 -> 변화 -> 영향",'
        '"interest_label":"high","keywords":["PyTorch","추론 성능","배포 영향"]}'
    )
```

Do not remove the existing `REQUEST_TIMEOUT_SECONDS = 120`, `MAX_KEYWORDS`, interest weights, thresholds, or content placeholders.

- [ ] **Step 4: Add env helper**

Add this helper in `ai/post_analysis/analyze_it_keywords.py` after `get_ollama_base_url`:

```python
def get_it_keyword_int_config(env_key: str, default: int) -> int:
    """IC02 정수 설정값을 환경변수에서 읽고 실패하면 기본값을 반환한다."""
    value = os.environ.get(env_key)
    if value is None or not value.strip():
        return default
    try:
        parsed = int(value.strip())
    except ValueError:
        return default
    if parsed < AnalyzeItKeywordsConfig.MIN_POSITIVE_CONFIG_VALUE:
        return default
    return parsed
```

- [ ] **Step 5: Run config tests and verify pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest ai\post_analysis\tests\unit\test_l0_it_keywords.py::test_pa_l0_itkw_009_preprocessing_config_defaults ai\post_analysis\tests\unit\test_l0_it_keywords.py::test_pa_l0_itkw_010_int_config_env_override ai\post_analysis\tests\unit\test_l0_it_keywords.py::test_pa_l0_itkw_011_int_config_falls_back_for_invalid_values -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```powershell
git add ai\post_analysis\common\constant.py ai\post_analysis\analyze_it_keywords.py ai\post_analysis\tests\unit\test_l0_it_keywords.py
git commit -m "feat: add ic02 preprocessing config"
```

---

### Task 2: Add Extractive Preprocessing Helpers

**Files:**
- Modify: `ai/post_analysis/analyze_it_keywords.py`
- Modify: `ai/post_analysis/tests/unit/test_l0_it_keywords.py`

- [ ] **Step 1: Write failing preprocessing tests**

Append these tests to `ai/post_analysis/tests/unit/test_l0_it_keywords.py`:

```python
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
```

Replace the previous `from analyze_it_keywords import` block with the block above so imports stay organized.

Append the new tests:

```python
def test_pa_l0_itkw_012_short_content_keeps_normalized_original() -> None:
    """PA-L0-ITKW-012 [정상]: 짧은 원문은 의미 압축 없이 정규화 결과를 그대로 쓴다."""
    original = "첫 줄&nbsp;내용\r\n\r\n둘째 줄  내용"

    compressed = compress_it_content("AI 릴리스", original)

    assert compressed == "첫 줄 내용\n\n둘째 줄 내용"


def test_pa_l0_itkw_013_long_content_is_compressed_under_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PA-L0-ITKW-013 [정상]: 긴 원문은 max chars 이하의 원문 발췌문으로 압축된다."""
    monkeypatch.setenv(AnalyzeItKeywordsConfig.MAX_CONTENT_CHARS_ENV_KEY, "220")
    monkeypatch.setenv(AnalyzeItKeywordsConfig.MAX_CONTENT_UNITS_ENV_KEY, "3")
    long_content = "\n\n".join(
        [
            "AI 모델 업데이트가 공개됐고 추론 성능 개선이 핵심입니다.",
            "행사장 주변 소식과 일정 안내입니다.",
            "GPU 비용과 배포 자동화 영향이 개발자에게 중요합니다.",
            "커뮤니티 댓글은 API 변경과 라이선스 리스크를 주로 언급합니다.",
            "마지막으로 보안 취약점 대응 일정이 정리됐습니다.",
        ]
    )

    compressed = compress_it_content("AI 모델 업데이트", long_content)

    assert len(compressed) <= 220
    assert len(compressed) < len(normalize_it_content(long_content))
    validate_preprocessed_content(
        normalize_it_content(long_content),
        compressed,
        220,
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
    """PA-L0-ITKW-016 [경계]: 긴 단일 문단은 문장 단위 후보로 분리된다."""
    paragraph = (
        "AI 모델 업데이트가 공개됐습니다. "
        "추론 성능 개선이 핵심입니다. "
        "GPU 비용과 배포 자동화 영향이 개발자에게 중요합니다."
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
```

- [ ] **Step 2: Run preprocessing tests and verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest ai\post_analysis\tests\unit\test_l0_it_keywords.py::test_pa_l0_itkw_012_short_content_keeps_normalized_original ai\post_analysis\tests\unit\test_l0_it_keywords.py::test_pa_l0_itkw_013_long_content_is_compressed_under_budget ai\post_analysis\tests\unit\test_l0_it_keywords.py::test_pa_l0_itkw_014_validation_rejects_text_not_in_original ai\post_analysis\tests\unit\test_l0_it_keywords.py::test_pa_l0_itkw_015_validation_rejects_uncompressed_long_content ai\post_analysis\tests\unit\test_l0_it_keywords.py::test_pa_l0_itkw_016_long_paragraph_splits_by_sentence ai\post_analysis\tests\unit\test_l0_it_keywords.py::test_pa_l0_itkw_017_preprocess_row_uses_env_limits -v
```

Expected: FAIL because preprocessing helpers are not implemented.

- [ ] **Step 3: Add `html` import**

Modify the imports at the top of `ai/post_analysis/analyze_it_keywords.py`:

```python
import html
import json
```

- [ ] **Step 4: Add preprocessing helpers**

Add this code after `_text_or_empty` in `ai/post_analysis/analyze_it_keywords.py`:

```python
def normalize_it_content(content: object) -> str:
    """IC02 content를 의미 변경 없이 비교 가능한 텍스트로 정규화한다."""
    text = html.unescape(_text_or_empty(content))
    text = re.sub(AnalyzeItKeywordsConfig.LINE_BREAK_PATTERN, "\n", text)
    text = re.sub(AnalyzeItKeywordsConfig.INLINE_SPACE_PATTERN, " ", text)
    text = re.sub(AnalyzeItKeywordsConfig.MULTI_BLANK_LINE_PATTERN, "\n\n", text)
    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(AnalyzeItKeywordsConfig.PARAGRAPH_SPLIT_PATTERN, text)
        if paragraph.strip()
    ]
    return AnalyzeItKeywordsConfig.NORMALIZED_PARAGRAPH_SEPARATOR.join(paragraphs)


def split_content_units(content: str, max_unit_chars: int) -> list[str]:
    """정규화된 content를 문단 우선, 긴 문단은 문장 단위로 나눈다."""
    normalized = normalize_it_content(content)
    if not normalized:
        return []

    units: list[str] = []
    paragraphs = re.split(AnalyzeItKeywordsConfig.PARAGRAPH_SPLIT_PATTERN, normalized)
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(paragraph) <= max_unit_chars:
            units.append(paragraph)
            continue
        sentences = [
            sentence.strip()
            for sentence in re.split(AnalyzeItKeywordsConfig.SENTENCE_SPLIT_PATTERN, paragraph)
            if sentence.strip()
        ]
        units.extend(sentences if sentences else [paragraph])
    return units


def _title_tokens(title: str) -> set[str]:
    """제목에서 unit scoring에 사용할 토큰을 추출한다."""
    return {
        token.lower()
        for token in re.findall(AnalyzeItKeywordsConfig.WORD_PATTERN, title)
        if token.strip()
    }


def _score_content_unit(
    unit: str,
    *,
    title_tokens: set[str],
    index: int,
    last_index: int,
) -> tuple[bool, bool, int, int, int]:
    """LLM 없이 deterministic 기준으로 content unit 중요도를 계산한다."""
    lowered = unit.lower()
    overlap_count = sum(
        1
        for token in title_tokens
        if token and token in lowered
    )
    important_count = sum(
        1
        for term in AnalyzeItKeywordsConfig.IMPORTANT_TERMS
        if term.lower() in lowered
    )
    number_count = len(re.findall(AnalyzeItKeywordsConfig.NUMBER_PATTERN, unit))
    return (
        index == 0,
        index == last_index,
        overlap_count,
        important_count,
        number_count,
    )


def _fit_units_to_budget(units: list[str], max_chars: int, max_units: int) -> list[str]:
    """원문 순서를 유지하면서 선택된 unit을 글자 수와 개수 예산에 맞춘다."""
    selected: list[str] = []
    current_chars = 0
    separator_len = len(AnalyzeItKeywordsConfig.NORMALIZED_PARAGRAPH_SEPARATOR)
    for unit in units:
        next_len = len(unit) if not selected else len(unit) + separator_len
        if len(selected) >= max_units:
            break
        if current_chars + next_len > max_chars:
            continue
        selected.append(unit)
        current_chars += next_len
    return selected


def select_content_units(
    title: object,
    units: list[str],
    max_chars: int,
    max_units: int,
) -> list[str]:
    """중요도와 원문 순서를 기준으로 LLM 입력에 포함할 unit을 고른다."""
    if not units:
        return []

    title_tokens = _title_tokens(_text_or_empty(title))
    last_index = len(units) - 1
    ranked = sorted(
        enumerate(units),
        key=lambda item: (
            _score_content_unit(
                item[1],
                title_tokens=title_tokens,
                index=item[0],
                last_index=last_index,
            ),
            -item[0],
        ),
        reverse=True,
    )
    selected_indexes = sorted(index for index, _unit in ranked[:max_units])
    ranked_units = [units[index] for index in selected_indexes]
    return _fit_units_to_budget(ranked_units, max_chars, max_units)


def validate_preprocessed_content(original: str, compressed: str, max_chars: int) -> None:
    """압축 결과가 원문 발췌이고 긴 원문에서 실제 압축됐는지 검증한다."""
    normalized_original = normalize_it_content(original)
    normalized_compressed = normalize_it_content(compressed)
    if not normalized_compressed:
        raise ValueError("IC02 전처리 결과가 비어 있습니다.")

    units = split_content_units(normalized_compressed, len(normalized_compressed))
    for unit in units:
        if unit not in normalized_original:
            raise ValueError("IC02 전처리 결과에 원문에 없는 문장이 포함됐습니다.")

    if len(normalized_original) > max_chars:
        if len(normalized_compressed) >= len(normalized_original):
            raise ValueError("IC02 긴 원문이 실제로 압축되지 않았습니다.")
        if len(normalized_compressed) > max_chars:
            raise ValueError("IC02 전처리 결과가 최대 길이를 초과했습니다.")


def compress_it_content(
    title: object,
    content: object,
    max_chars: int | None = None,
    max_units: int | None = None,
    max_unit_chars: int | None = None,
) -> str:
    """IC02 content를 원문 발췌 기반 compressed_content로 만든다."""
    resolved_max_chars = (
        max_chars
        if max_chars is not None
        else get_it_keyword_int_config(
            AnalyzeItKeywordsConfig.MAX_CONTENT_CHARS_ENV_KEY,
            AnalyzeItKeywordsConfig.MAX_CONTENT_CHARS,
        )
    )
    resolved_max_units = (
        max_units
        if max_units is not None
        else get_it_keyword_int_config(
            AnalyzeItKeywordsConfig.MAX_CONTENT_UNITS_ENV_KEY,
            AnalyzeItKeywordsConfig.MAX_CONTENT_UNITS,
        )
    )
    resolved_max_unit_chars = (
        max_unit_chars
        if max_unit_chars is not None
        else get_it_keyword_int_config(
            AnalyzeItKeywordsConfig.MAX_UNIT_CHARS_ENV_KEY,
            AnalyzeItKeywordsConfig.MAX_UNIT_CHARS,
        )
    )

    original = normalize_it_content(content)
    if len(original) <= resolved_max_chars:
        validate_preprocessed_content(original, original, resolved_max_chars)
        return original

    units = split_content_units(original, resolved_max_unit_chars)
    selected = select_content_units(
        title,
        units,
        resolved_max_chars,
        resolved_max_units,
    )
    compressed = AnalyzeItKeywordsConfig.NORMALIZED_PARAGRAPH_SEPARATOR.join(selected)
    validate_preprocessed_content(original, compressed, resolved_max_chars)
    return compressed


def preprocess_it_content(row: dict | pd.Series) -> str:
    """IC02 row에서 LLM에 전달할 compressed_content를 만든다."""
    return compress_it_content(
        row.get(AnalysisColumn.TITLE.value),
        row.get(AnalysisColumn.CONTENT.value),
    )
```

- [ ] **Step 5: Run preprocessing tests and verify pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest ai\post_analysis\tests\unit\test_l0_it_keywords.py::test_pa_l0_itkw_012_short_content_keeps_normalized_original ai\post_analysis\tests\unit\test_l0_it_keywords.py::test_pa_l0_itkw_013_long_content_is_compressed_under_budget ai\post_analysis\tests\unit\test_l0_it_keywords.py::test_pa_l0_itkw_014_validation_rejects_text_not_in_original ai\post_analysis\tests\unit\test_l0_it_keywords.py::test_pa_l0_itkw_015_validation_rejects_uncompressed_long_content ai\post_analysis\tests\unit\test_l0_it_keywords.py::test_pa_l0_itkw_016_long_paragraph_splits_by_sentence ai\post_analysis\tests\unit\test_l0_it_keywords.py::test_pa_l0_itkw_017_preprocess_row_uses_env_limits -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```powershell
git add ai\post_analysis\analyze_it_keywords.py ai\post_analysis\tests\unit\test_l0_it_keywords.py
git commit -m "feat: add ic02 content preprocessing"
```

---

### Task 3: Use Compressed Content In Prompt And Timeout Config

**Files:**
- Modify: `ai/post_analysis/analyze_it_keywords.py`
- Modify: `ai/post_analysis/tests/unit/test_l0_it_keywords.py`

- [ ] **Step 1: Add failing prompt and timeout tests**

Append these tests to `ai/post_analysis/tests/unit/test_l0_it_keywords.py`:

```python
def test_pa_l0_itkw_018_prompt_uses_compressed_content_label(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PA-L0-ITKW-018 [정상]: prompt는 원문 전체가 아니라 검증된 compressed_content를 쓴다."""
    monkeypatch.setenv(AnalyzeItKeywordsConfig.MAX_CONTENT_CHARS_ENV_KEY, "120")
    raw_content = (
        "AI 모델 업데이트가 공개됐고 추론 성능 개선이 핵심입니다.\n\n"
        "행사 안내와 현장 분위기를 설명하는 긴 문단입니다.\n\n"
        "GPU 비용과 API 변경 영향이 개발자에게 중요합니다."
    )

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
    assert "행사 안내와 현장 분위기" not in prompt


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
```

Add `MagicMock` and `patch` imports if they are not already in `test_l0_it_keywords.py`:

```python
from unittest.mock import MagicMock, patch
```

Add `_ollama_chat_json` to the `from analyze_it_keywords import` block.

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest ai\post_analysis\tests\unit\test_l0_it_keywords.py::test_pa_l0_itkw_018_prompt_uses_compressed_content_label ai\post_analysis\tests\unit\test_l0_it_keywords.py::test_pa_l0_itkw_019_ollama_timeout_uses_env_override -v
```

Expected: FAIL because prompt still uses `[content]` and `_ollama_chat_json` still uses static timeout.

- [ ] **Step 3: Update prompt builder**

Replace `build_it_keyword_prompt` in `ai/post_analysis/analyze_it_keywords.py` with:

```python
def build_it_keyword_prompt(row: dict | pd.Series) -> str:
    """Gemma에 전달할 IC02 keyword user prompt를 만든다."""
    title = _text_or_empty(row.get(AnalysisColumn.TITLE.value))
    compressed_content = preprocess_it_content(row)
    interest = compute_interest_signal(row)
    prompt_lines = [
        *AnalyzeItKeywordsConfig.PROMPT_INSTRUCTIONS,
        "반환 JSON 스키마:",
        AnalyzeItKeywordsConfig.RESPONSE_SCHEMA_EXAMPLE,
        "제약:",
        f"- keywords는 3개 이상 {AnalyzeItKeywordsConfig.MAX_KEYWORDS}개 이하입니다.",
        "- keywords에는 기술명, 제품명, 프레임워크, 영향, 리스크, 사용 포인트를 함께 넣습니다.",
        "",
        f"{AnalyzeItKeywordsConfig.TITLE_PROMPT_LABEL}\n{title}",
        f"{AnalyzeItKeywordsConfig.COMPRESSED_CONTENT_PROMPT_LABEL}\n{compressed_content}",
        f"{AnalyzeItKeywordsConfig.INTEREST_PROMPT_LABEL}\n{interest['description']}",
    ]
    return "\n".join(prompt_lines)
```

- [ ] **Step 4: Update Ollama timeout**

Replace the timeout argument inside `_ollama_chat_json` with:

```python
            timeout=get_it_keyword_int_config(
                AnalyzeItKeywordsConfig.REQUEST_TIMEOUT_SECONDS_ENV_KEY,
                AnalyzeItKeywordsConfig.REQUEST_TIMEOUT_SECONDS,
            ),
```

- [ ] **Step 5: Run prompt and timeout tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest ai\post_analysis\tests\unit\test_l0_it_keywords.py::test_pa_l0_itkw_018_prompt_uses_compressed_content_label ai\post_analysis\tests\unit\test_l0_it_keywords.py::test_pa_l0_itkw_019_ollama_timeout_uses_env_override -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```powershell
git add ai\post_analysis\analyze_it_keywords.py ai\post_analysis\tests\unit\test_l0_it_keywords.py
git commit -m "feat: use ic02 compressed content prompt"
```

---

### Task 4: Verify Validation Failure Skips LLM And Merge

**Files:**
- Modify: `ai/post_analysis/tests/unit/test_l3_analyze_it_keywords_indirect.py`

- [ ] **Step 1: Write failing orchestration skip test**

Append this test to `ai/post_analysis/tests/unit/test_l3_analyze_it_keywords_indirect.py`:

```python
@patch("analyze_it_keywords.merge_analysis_data")
@patch("analyze_it_keywords._ollama_chat_json")
@patch("analyze_it_keywords.preprocess_it_content")
@patch("analyze_it_keywords.get_crawling_data")
@patch("analyze_it_keywords.get_analysis_data")
def test_pa_l3_itkw_008_preprocessing_failure_skips_ollama_and_merge(
    mock_get_analysis: MagicMock,
    mock_get_crawling: MagicMock,
    mock_preprocess: MagicMock,
    mock_ollama_chat_json: MagicMock,
    mock_merge: MagicMock,
) -> None:
    """전처리 검증 실패 row는 Ollama 호출과 MERGE 없이 skip된다."""
    mock_get_analysis.return_value = pd.DataFrame(
        {
            AnalysisColumn.CRAWLING_ID.value: [501],
            AnalysisColumn.TITLE.value: ["AI 모델 업데이트"],
            AnalysisColumn.CONTENT.value: ["AI 모델 업데이트가 공개됐습니다."],
            AnalysisColumn.KEYWORDS.value: [pd.NA],
            AnalysisColumn.INFORMATION_CD.value: [CodeTable.INFORMATION_IT_INFO.value],
        }
    )
    mock_get_crawling.return_value = pd.DataFrame()
    mock_preprocess.side_effect = ValueError("IC02 전처리 결과에 원문에 없는 문장이 포함됐습니다.")

    analyze_it_keywords()

    mock_ollama_chat_json.assert_not_called()
    mock_merge.assert_not_called()
```

- [ ] **Step 2: Run skip test and verify pass or failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest ai\post_analysis\tests\unit\test_l3_analyze_it_keywords_indirect.py::test_pa_l3_itkw_008_preprocessing_failure_skips_ollama_and_merge -v
```

Expected: PASS if Task 3 routes prompt creation through `preprocess_it_content` before `_ollama_chat_json`. If it fails, the expected fix is in Step 3.

- [ ] **Step 3: Apply only the required fix if Step 2 fails**

If `_ollama_chat_json` was called, modify `extract_it_keywords` so it only calls Ollama after `build_it_keyword_prompt(row)` succeeds:

```python
def extract_it_keywords(row: dict | pd.Series) -> ItKeywordResult:
    """IC02 row 하나를 Ollama로 분석해 요약, 흐름, 키워드를 추출한다."""
    prompt = build_it_keyword_prompt(row)
    return ItKeywordResult(**_ollama_chat_json(prompt))
```

This is the existing intended structure. Do not add fallback truncation or direct Ollama calls around preprocessing.

- [ ] **Step 4: Run orchestration tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest ai\post_analysis\tests\unit\test_l3_analyze_it_keywords_indirect.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```powershell
git add ai\post_analysis\tests\unit\test_l3_analyze_it_keywords_indirect.py ai\post_analysis\analyze_it_keywords.py
git commit -m "test: verify ic02 preprocessing skip"
```

If Step 3 did not require a code change, commit only the test file.

---

### Task 5: Focused Verification And Scope Check

**Files:**
- Verify only.

- [ ] **Step 1: Run IC02 focused tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest ai\post_analysis\tests\unit\test_l0_it_keywords.py ai\post_analysis\tests\unit\test_l3_analyze_it_keywords_indirect.py -v
```

Expected: PASS.

- [ ] **Step 2: Run IC01 guard tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest ai\post_analysis\tests\unit\test_l2_analyze_sentimental_indirect.py ai\post_analysis\tests\unit\test_l3_analyze_keywords_bert_indirect.py -v
```

Expected: PASS. This confirms existing IC01 sentiment and BERT keyword behavior remains intact.

- [ ] **Step 3: Run full post_analysis suite**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest ai\post_analysis -v
```

Expected: PASS.

- [ ] **Step 4: Inspect changed file scope**

Run:

```powershell
git diff --stat HEAD
```

Expected: changed source files are limited to the scope guard list. There must be no changes under `etl/meal`, `etl/it_news`, `ai/postmake_pipeline`, `ai/post_analysis/pipeline.py`, `ai/post_analysis/postgresql`, or DB schema files.

- [ ] **Step 5: Inspect new mutable globals**

Run:

```powershell
rg "^[A-Z_]+\\s*=\\s*\\[|^[a-zA-Z_]+_cache\\s*=|^[a-zA-Z_]+_state\\s*=|global " ai\post_analysis\analyze_it_keywords.py ai\post_analysis\common\constant.py
```

Expected: no mutable module-level cache, state, or `global` statement is introduced. Immutable config class constants in `AnalyzeItKeywordsConfig` are acceptable.

- [ ] **Step 6: Commit verification fixes only if files changed**

Run:

```powershell
git status --short
```

If verification caused a small fix, commit it:

```powershell
git add ai\post_analysis\common\constant.py ai\post_analysis\analyze_it_keywords.py ai\post_analysis\tests\unit\test_l0_it_keywords.py ai\post_analysis\tests\unit\test_l3_analyze_it_keywords_indirect.py
git commit -m "test: verify ic02 preprocessing"
```

If there are no changes after Task 4, do not create an empty commit.

---

## Self-Review Checklist

- Spec coverage:
  - IC02-only scope is enforced by the scope guard and Task 5 diff check.
  - Extractive compression is implemented by `normalize_it_content`, `split_content_units`, `select_content_units`, and `compress_it_content`.
  - Source validation is implemented by `validate_preprocessed_content`.
  - Actual compression validation for long content is implemented by `validate_preprocessed_content`.
  - Validation failure skips LLM and merge through Task 4.
  - Prompt uses `[compressed_content]` through Task 3.
  - Timeout, max chars, max units, and max unit chars are env configurable through Task 1 and Task 3.
  - Hardcoding is minimized by moving policy values and prompt strings to `AnalyzeItKeywordsConfig`.
  - Mutable global state is explicitly checked in Task 5.
- Marker scan: no unresolved implementation markers are present.
- Type consistency:
  - `get_it_keyword_int_config(env_key: str, default: int) -> int` is used consistently.
  - `compress_it_content(title, content, max_chars, max_units, max_unit_chars) -> str`, `preprocess_it_content(row) -> str`, and `validate_preprocessed_content(original, compressed, max_chars) -> None` are used consistently.
  - Existing `analyze_it_keywords(max_rows: int | None = None, overwrite: bool = False)` remains unchanged.
