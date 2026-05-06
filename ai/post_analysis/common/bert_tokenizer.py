# 로그 
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 패키지
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from torch.nn import functional as F
import torch


class BertTokenizer:
    """
    모델이름을 constant에서 상수로 받아서 처리 (models > bert로 받아옴 )
    init에서 토크나이저와 모델 로드 진행 

    """

    def __init__(self, model_name: str):
        # 사용할 모델 명 
        MODEL_NAME = "sangrimlee/bert-base-multilingual-cased-nsmc"
        # 토크나이저 로드
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        # 모델 로드
        model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)


        self.model_name = model_name
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)

    def tokenize(self, text: str) -> dict:
        return self.tokenizer.encode_plus(text, return_tensors="pt")

    def decode(self, token_ids: list) -> str:
        return self.tokenizer.decode(token_ids)

    def predict_sentiment(text: str) -> dict:
        inputs = tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=512
        )

        with torch.no_grad():
            outputs = model(**inputs)
            probs = F.softmax(outputs.logits, dim=-1)[0]

        negative_score = probs[0].item()
        positive_score = probs[1].item()

        return {
            "sentimental": "positive" if positive_score >= negative_score else "negative",
            "score": round(max(positive_score, negative_score), 4),
            "positive_score": round(positive_score, 4),
            "negative_score": round(negative_score, 4)
        }
