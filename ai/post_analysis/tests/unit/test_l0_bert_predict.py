"""PA-L0-BERT: BertTokenizer.predict_sentiment (Level 0, 모델 mock)."""

from unittest.mock import MagicMock

import torch

from common.bert_tokenizer import BertTokenizer
from common.constant import AnalyzeSentimentalConfig, SentimentLabel, SentimentResultKey


def _tokenizer_with_logits(neg: float, pos: float) -> BertTokenizer:
    """softmax 입력용 logits를 고정한 mock BertTokenizer."""
    tok = BertTokenizer.__new__(BertTokenizer)
    tok.tokenizer = MagicMock()
    tok.tokenizer.return_value = {"input_ids": torch.zeros(1, 4)}

    logits = torch.tensor([[neg, pos]], dtype=torch.float32)
    mock_out = MagicMock()
    mock_out.logits = logits

    mock_model = MagicMock()
    mock_model.return_value = mock_out
    tok.model = mock_model
    return tok


def test_pa_l0_bert_001_positive_label() -> None:
    """PA-L0-BERT-001 [불변]: positive 확률 우세 시 sentimental=positive, score=max(p,n)."""
    tok = _tokenizer_with_logits(0.2, 0.8)
    result = tok.predict_sentiment("좋아요")
    assert result[SentimentResultKey.SENTIMENTAL.value] == SentimentLabel.POSITIVE.value
    assert result[SentimentResultKey.POSITIVE_SCORE.value] > result[SentimentResultKey.NEGATIVE_SCORE.value]
    assert result[SentimentResultKey.SCORE.value] == result[SentimentResultKey.POSITIVE_SCORE.value]


def test_pa_l0_bert_002_negative_label() -> None:
    """PA-L0-BERT-002 [불변]: negative 확률 우세 시 sentimental=negative."""
    tok = _tokenizer_with_logits(0.7, 0.3)
    result = tok.predict_sentiment("별로")
    assert result[SentimentResultKey.SENTIMENTAL.value] == SentimentLabel.NEGATIVE.value


def test_pa_l0_bert_003_result_keys() -> None:
    """PA-L0-BERT-003 [불변]: 결과 dict에 SentimentResultKey 전 키 존재."""
    tok = _tokenizer_with_logits(0.4, 0.6)
    result = tok.predict_sentiment("text")
    for key in SentimentResultKey:
        assert key.value in result


def test_pa_l0_bert_004_tie_goes_positive() -> None:
    """PA-L0-BERT-004 [경계]: 동률이면 positive (>= 규칙)."""
    tok = _tokenizer_with_logits(0.5, 0.5)
    result = tok.predict_sentiment("tie")
    assert result[SentimentResultKey.SENTIMENTAL.value] == SentimentLabel.POSITIVE.value


def test_pa_l0_bert_005_score_decimal_places() -> None:
    """PA-L0-BERT-005 [불변]: score·positive_score 소수 자릿수 설정 준수."""
    tok = _tokenizer_with_logits(0.1111, 0.8888)
    result = tok.predict_sentiment("x")
    dec = AnalyzeSentimentalConfig.SCORE_DECIMAL_PLACES
    assert result[SentimentResultKey.POSITIVE_SCORE.value] == round(
        result[SentimentResultKey.POSITIVE_SCORE.value], dec
    )
    assert result[SentimentResultKey.SCORE.value] >= result[SentimentResultKey.NEGATIVE_SCORE.value]
