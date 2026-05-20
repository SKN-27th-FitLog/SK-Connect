"""Hugging Face `transformers` 기반 감성 분류기 헬퍼."""

# 패키지
import torch
from torch.nn import functional as F
from transformers import AutoModelForSequenceClassification, AutoTokenizer

# 모듈
from common.constant import AnalyzeSentimentalConfig, SentimentLabel, SentimentResultKey
from common.singleton import Singleton


class BertTokenizer(metaclass=Singleton):
    """토크나이저·분류 모델을 로드하고 문장 단위 감성 추론을 수행한다.

    기본 모델명은 `AnalyzeSentimentalConfig.MODEL_NAME`과 동일하다.
    """

    def __init__(self, model_name: str | None = None):
        """HF 허브에서 토크나이저와 시퀀스 분류 모델을 불러온다.

        Args:
            model_name: 미지정 시 ``AnalyzeSentimentalConfig.MODEL_NAME`` 사용.

        Note:
            함수 유형: E — 외부 연동 (Hugging Face Hub)
            안전성: Level 1 — 네트워크·디스크 캐시 읽기, DB/운영 데이터 미변경
            부작용: 모델·토크나이저 메모리 로드
        """
        name = model_name or AnalyzeSentimentalConfig.MODEL_NAME
        self.model_name = name
        # 토크나이저 로드
        self.tokenizer = AutoTokenizer.from_pretrained(name)
        # 모델 로드
        self.model = AutoModelForSequenceClassification.from_pretrained(name)

    def tokenize(self, text: str) -> dict:
        """문장을 PyTorch 입력 텐서로 인코딩한다.

        Args:
            text: 감성 분류 대상 문장.

        Returns:
            ``encode_plus(..., return_tensors="pt")`` 결과 dict.

        Note:
            함수 유형: A — 순수 계산 (추론 전처리)
            안전성: Level 0 — 입력만으로 결과 생성 (모델은 이미 로드됨)
        """
        return self.tokenizer.encode_plus(text, return_tensors="pt")

    def decode(self, token_ids: list) -> str:
        """토큰 id 시퀀스를 원문 문자열로 복원한다.

        Args:
            token_ids: 토크나이저가 반환한 id 목록.

        Returns:
            디코딩된 문자열.

        Note:
            함수 유형: A — 순수 계산
            안전성: Level 0
        """
        return self.tokenizer.decode(token_ids)

    def predict_sentiment(self, text: str) -> dict:
        """문장에 대한 긍·부정 softmax 확률과 대표 라벨 dict를 반환한다.

        ``SentimentResultKey`` 키(``sentimental``, ``score``, ``positive_score``,
        ``negative_score``)로 결과를 담는다. ``score``는 두 클래스 확률 중 큰 값이다.

        Args:
            text: 감성 분류 대상 본문.

        Returns:
            감성 라벨·점수 dict.

        Note:
            함수 유형: A — 순수 계산 (로컬 추론)
            안전성: Level 0 — DB·API 쓰기 없음
            불변 규칙: ``positive_score >= negative_score`` 이면 ``sentimental=positive``
        """
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=AnalyzeSentimentalConfig.MAX_SEQUENCE_LENGTH,
        )

        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = F.softmax(outputs.logits, dim=-1)[0]

        negative_score = probs[0].item()
        positive_score = probs[1].item()
        dec = AnalyzeSentimentalConfig.SCORE_DECIMAL_PLACES
        sk = SentimentResultKey
        label = (
            SentimentLabel.POSITIVE.value
            if positive_score >= negative_score
            else SentimentLabel.NEGATIVE.value
        )

        return {
            sk.SENTIMENTAL.value: label,
            sk.SCORE.value: round(max(positive_score, negative_score), dec),
            sk.POSITIVE_SCORE.value: round(positive_score, dec),
            sk.NEGATIVE_SCORE.value: round(negative_score, dec),
        }
