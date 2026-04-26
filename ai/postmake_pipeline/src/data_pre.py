from konlpy.tag import Okt
from textrankr import TextRank

from src.logging_config import set_logging
from src.merge_utils import apply_merge_rules
logger = set_logging()

# 동일 title 기준 merge
# merge 후 content 요약
# 키워드 중복 제거

class DataPreprocessing:
    def __init__(self):
        self.okt = Okt()
        self.textrank = TextRank(tokenizer=self.okt.nouns)
        self.data = []

    def merge_same_title(self):
        """동일 title + map_id 기준 merge"""
        merged_data: dict[tuple[str, str], dict] = {}
        concat_keys = ['content', 'metadata', 'keywords']
        fill_if_none_keys = ['article_url', 'author', 'view_count', 'comment_count', 'category_cd', 'map_id', 'shop_name', 'menu_name', 'menu_price']

        for row in self.data:
            map_id = str(row.get('map_id') or '')
            merge_key = (str(row.get('title') or ''), map_id)

            if merge_key not in merged_data: #title+map_id가 없으면 추가
                merged_data[merge_key] = row.copy() #row를 복사하여 merged_data에 추가
                continue

            target = merged_data[merge_key] #title+map_id가 있으면 target에 추가

            apply_merge_rules(
                target=target,
                incoming=row,
                concat_keys=concat_keys,
                fill_if_none_keys=fill_if_none_keys
            )

        self.data = list(merged_data.values())


    def summarize_content(self):
        """content 요약"""
        for row in self.data:
            row['summary'] = self.textrank.summarize(row['content'], num_sentences=5, verbose=False) #content 요약
        return self.data


    def extract_keywords(self):
        """키워드 추출"""
        for row in self.data:
            content = row['content']
            tokens = self.okt.nouns(content)
            row['keywords'] += ' ' + " ".join(tokens)

    def remove_duplicate_keywords(self):
        """키워드 중복 제거"""
        for row in self.data:
            if row['keywords'] is not None:
                keywords = row['keywords'].split(' ')
                row['keywords'] = ' '.join(dict.fromkeys(keywords))
        return self.data

    def execute(self, data:list[dict])->list[dict]:
        """데이터 전처리"""
        self.data = data
        self.merge_same_title() #동일 title 기준 merge
        self.extract_keywords() #키워드 추출
        self.summarize_content() #content 요약
        self.remove_duplicate_keywords() #키워드 중복 제거
        return self.data
