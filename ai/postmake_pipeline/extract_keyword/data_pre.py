from konlpy.tag import Okt
from textrankr import TextRank

from common.logging_config import set_logging
logger = set_logging()

# 동일 title 기준 merge
# merge 후 content 요약
# 키워드 중복 제거

class DataPreprocessing:
    def __init__(self):
        self.okt = Okt()
        self.textrank = TextRank(tokenizer=self.okt.nouns)
        self.data = []

    def merge_same_title(self): # 동일한 title + ??? 으로 merge
        pass