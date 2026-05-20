"""PA-L0-BERT: predict_sentiment (model mock)."""

from unittest.mock import MagicMock

import torch

from common.bert_tokenizer import BertTokenizer
from common.constant import AnalyzeSentimentalConfig, SentimentLabel, SentimentResultKey


def _tokenizer_with_logits(neg: float, pos: float) -> BertTokenizer:
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
    tok = _tokenizer_with_logits(0.2, 0.8)
    result = tok.predict_sentiment("좋아요")
    assert result[SentimentResultKey.SENTIMENTAL.value] == SentimentLabel.POSITIVE.value
    assert result[SentimentResultKey.POSITIVE_SCORE.value] > result[SentimentResultKey.NEGATIVE_SCORE.value]
    assert result[SentimentResultKey.SCORE.value] == result[SentimentResultKey.POSITIVE_SCORE.value]


def test_pa_l0_bert_002_negative_label() -> None:
    tok = _tokenizer_with_logits(0.7, 0.3)
    result = tok.predict_sentiment("별로")
    assert result[SentimentResultKey.SENTIMENTAL.value] == SentimentLabel.NEGATIVE.value


def test_pa_l0_bert_003_result_keys() -> None:
    tok = _tokenizer_with_logits(0.4, 0.6)
    result = tok.predict_sentiment("text")
    for key in SentimentResultKey:
        assert key.value in result


def test_pa_l0_bert_004_tie_goes_positive() -> None:
    tok = _tokenizer_with_logits(0.5, 0.5)
    result = tok.predict_sentiment("tie")
    assert result[SentimentResultKey.SENTIMENTAL.value] == SentimentLabel.POSITIVE.value


def test_pa_l0_bert_005_score_decimal_places() -> None:
    tok = _tokenizer_with_logits(0.1111, 0.8888)
    result = tok.predict_sentiment("x")
    dec = AnalyzeSentimentalConfig.SCORE_DECIMAL_PLACES
    assert result[SentimentResultKey.POSITIVE_SCORE.value] == round(
        result[SentimentResultKey.POSITIVE_SCORE.value], dec
    )
    assert result[SentimentResultKey.SCORE.value] >= result[SentimentResultKey.NEGATIVE_SCORE.value]
