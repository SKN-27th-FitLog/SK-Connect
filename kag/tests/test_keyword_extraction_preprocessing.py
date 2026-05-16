from kag_graph.extraction.models import MorphToken
from kag_graph.extraction.preprocessing.action_signal_extractor import ActionSignalExtractor
from kag_graph.extraction.preprocessing.candidate_phrase_builder import CandidatePhraseBuilder
from kag_graph.extraction.preprocessing.korean_morph_analyzer import KoreanMorphAnalyzer
from kag_graph.extraction.preprocessing.token_filter import TokenFilter


def test_korean_morph_analyzer_keeps_documented_pos_tags():
    tokens = KoreanMorphAnalyzer().analyze("OpenAI가 GPT-5를 공개하고 AI 반도체를 출시했다.")

    forms = [token.form for token in tokens]

    assert "OpenAI" in forms
    assert "GPT" in forms
    assert "AI" in forms
    assert "공개" in forms
    assert "출시" in forms


def test_token_filter_removes_noise_and_keeps_allowed_action_verbs():
    tokens = [
        MorphToken("A", "SL"),
        MorphToken("123", "SN"),
        MorphToken("AI", "SL"),
        MorphToken("출시", "VV"),
        MorphToken("했다", "EF"),
        MorphToken("매우긴문자열" * 10, "NNG"),
    ]

    filtered = TokenFilter().filter(tokens)

    assert [token.form for token in filtered] == ["AI", "출시"]


def test_candidate_phrase_builder_creates_single_tokens_and_documented_ngrams():
    tokens = [
        MorphToken("생성형", "NNG"),
        MorphToken("AI", "SL"),
        MorphToken("반도체", "NNG"),
        MorphToken("출시", "VV"),
    ]

    candidates = CandidatePhraseBuilder().build("article-1", tokens, title="생성형 AI", content="AI 반도체 출시")
    texts = [candidate.text for candidate in candidates]

    assert "생성형" in texts
    assert "생성형 AI" in texts
    assert "AI 반도체" in texts
    assert "출시" not in texts


def test_action_signal_extractor_stores_important_verbs_as_event_signals_only():
    signals = ActionSignalExtractor().extract("OpenAI가 GPT를 공개하고 서비스를 출시했다. 해킹 사고도 있었다.")

    assert [signal.action_type for signal in signals] == ["RELEASE", "ANNOUNCEMENT", "SECURITY_RISK"]
    assert [signal.matched_text for signal in signals] == ["출시", "공개", "해킹"]
