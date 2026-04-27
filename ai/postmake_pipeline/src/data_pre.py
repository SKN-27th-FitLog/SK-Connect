from konlpy.tag import Okt
from textrankr import TextRank
import re

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
            title = str(row.get('title') or '')
            map_id = row.get('map_id')
            # map_id가 없으면 row 단위(crawling_id)로 유지해 과도 merge 방지
            if map_id is None:
                merge_key = (title, f"crawling:{row.get('crawling_id')}")
            else:
                merge_key = (title, str(map_id))

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
            content = (row.get('content') or '').strip()
            if not content:
                row['summary'] = []
                continue
            row['summary'] = self.textrank.summarize(content, num_sentences=5, verbose=False) #content 요약
        return self.data


    def extract_keywords(self):
        """키워드 추출"""
        for row in self.data:
            content = row.get('content') or ''
            tokens = self.okt.nouns(content)
            base_keywords = row.get('keywords') or ''
            row['keywords'] = (base_keywords + ' ' + " ".join(tokens)).strip()

    def remove_duplicate_keywords(self):
        """키워드 중복 제거"""
        for row in self.data:
            raw_keywords = row.get('keywords')
            if raw_keywords is None:
                continue

            # 공백/쉼표/슬래시/파이프/세미콜론 등 구분자를 모두 허용해 토큰화
            tokens = re.split(r"[\s,;/|]+", str(raw_keywords))
            normalized_tokens: list[str] = []
            seen: set[str] = set()

            for token in tokens:
                cleaned = token.strip().strip(".,!?\"'`()[]{}")
                if not cleaned:
                    continue
                # 대소문자 차이로 같은 키워드가 중복되는 경우를 함께 제거
                key = cleaned.casefold()
                if key in seen:
                    continue
                seen.add(key)
                normalized_tokens.append(cleaned)

            row['keywords'] = ' '.join(normalized_tokens)
        return self.data

    def execute(self, data:list[dict])->list[dict]:
        """데이터 전처리"""
        self.data = data
        self.merge_same_title() #동일 title 기준 merge
        self.extract_keywords() #키워드 추출
        self.summarize_content() #content 요약
        self.remove_duplicate_keywords() #키워드 중복 제거
        return self.data
