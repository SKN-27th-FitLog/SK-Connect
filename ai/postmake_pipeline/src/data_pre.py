from konlpy.tag import Okt
from logging_config import set_logging
logger = set_logging()

# 동일 title 기준 merge
# merge 후 content 요약
# 키워드 중복 제거

class DataPreprocessing:
    def __init__(self):
        self.okt = Okt()
        self.data = []

    @staticmethod
    def merge_same_title(self):
        """동일 title 기준 merge"""
        merged_data = []

        for row in self.data:
            if row['title'] in merged_data:

                # 동일 title 기준 content, metadata, crawling_id, keywords +=
                keys = ['content', 'metadata', 'crawling_id', 'keywords']
                for k in keys:
                    if merged_data[row['title']][k] is None:
                        merged_data[row['title']][k] = row[k]
                        continue
                    merged_data[['title']][k] +=  ', ' + row[k]


                # 동일 title 기준 article_url, author, view_count, comment_count, category_cd, map_id 중복 없으면 추가
                key = ['article_url', 'author', 'view_count', 'comment_count', 'category_cd', 'map_id']
                for k in key:
                    if merged_data[row['title']][k] is None:
                        merged_data[row['title']][k] = row[k]
                        continue
                    merged_data[row['title']][k] +=  ', ' + row[k]

                # 동일 title 기준 created_at, updated_at 추가
                merged_data[row['title']]['created_at'] = min(merged_data[['title']]['created_at'], row['created_at'])
                merged_data[row['title']]['updated_at'] = max(merged_data[['title']]['updated_at'], row['updated_at'])

                continue

            elif row['title'] not in merged_data:
                merged_data.append(row)
                continue

        self.data.append(merged_data)

    @staticmethod
    def summarize_content(self):
        """content 요약"""
        summarized_data = ""
        okt = Okt()
        tokens = okt.nouns(self.data)
        summarized_data += " ".join(tokens)
        return summarized_data

    @staticmethod
    def remove_duplicate_keywords(self):
        pass

    @staticmethod
    def execute(self, data:list[dict]):
        self.data = data
        self.merge_same_title()
        self.summarize_content()
        self.remove_duplicate_keywords()
        return self.data