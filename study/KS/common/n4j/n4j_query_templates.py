from ast import With
import logging
from enum import Enum
from unittest import result

from sqlalchemy import Case

logger = logging.getLogger(__name__)

class CypherQueryTemplates(Enum):
    """다앙한 질문 유형을 Enum으로 관리하는 Cypher 탬플릿"""

    # 질문 분류 (카테고리에 따라 재사용할 탬플릿 키) - 해당 클래스 전역 변수
    NEWS_BY_CATEGORY = 'news_by_category'
    NEWS_BY_PUBLISHER = 'news_by_publisher'
    NEWS_BY_REPORTER = 'news_by_reporter'

    def __return_template(self) -> str:
        """Score는 해당 노드가 다른 노드들과 얼마나 많은 관계(edge를 가지고 있는지를 0 ~ 1 사이로 정규화 한 값이다. """ 
        # 각 조건에서 공통으로 사용하는 projection + score 계산 블록

        return """
        WITH n, p, r, 
            COUNT { (n)--() } AS relation_count

        // 1단계: 전체 relation_count 집계
        WITH collct({
            node: n,
            pub: p, 
            rep: r,
            count: relation_count
        }) AS results,
        max(relation_count) AS max_count,
        min(relation_count) AS min_count

        // 2단계: 리스트 다시 펼치기 
        UNWIND results AS result

        WITH 
        result.node AS n, 
        result.pub AS p,
        result.rep AS r,
        CASE 
            WHEN max_count = min_count THEN 0.5 
            ELSE(result.count - min_count) * 1.0 / (max_count - min_count)
        END AS score

        RETURN 
        n.title AS title,
        n.content AS content,
        p.name AS publisher_name,
        r.name AS reporter_name,
        n.publishDate AS publish_date,
        n.link AS news_link,
        score 
        ORDER BY score DESC
    """

    def build(self, **kwargs) -> str:
        """탬플릿 유형에 따라 Cypher 쿼리 생성"""
        if self is CypherQueryTemplates.NEWS_BY_CATEGORY:
            category_name = kwargs["category_name"]
            limit_no = kwargs["limit_no"]

            # 카테고리 기준으로 매칭한 뒤 공통 score 탬플릿 적용 

            return f"""
            MATCH (n:News)-[:BELONGS_TO]->(c:Category)
            WHERE c.name =~ '(?i).*{category_name}.*'
            MATCH (n)-[:PUBLISHED_BY]->(p:Publisher)
            MATCH (n)-[:WRITTEN_BY]->(r:Reporter)

            {self.__return_template()}
            LIMIT {limit_no}
            """
        if self is CypherQueryTemplates.NEWS_BY_PUBLISHER:
            publisher_name = kwargs["publisher_name"]
            limit_no = kwargs["limit_no"]
            # 특정 언론사가 발행한 뉴스들을 스코어링
            return f"""
            MATCH (n:News)-[:PUBLISHED_BY]->(p:Publisher)
            WHERE p.name =~ '(?i).*{publisher_name}.*'
            MATCH (n)-[:BELONGS_TO]->(c:Category)
            MATCH (n)-[:WRITTEN_BY]->(r:Reporter)
            
            {self.__return_template()}
            LIMIT {limit_no}
            """

        if self is CypherQueryTemplates.NEWS_BY_REPORTER:
            reporter_name = kwargs["reporter_name"]
            limit_no = kwargs["limit_no"]
            # 기자 기준으로 취재한 뉴스들을 노멀라이즈된 점수로 반환
            return f"""
            MATCH (n:News)-[:WRITTEN_BY]->(r:Reporter)
            WHERE r.name =~ '(?i).*{reporter_name}.*'
            MATCH (n)-[:BELONGS_TO]->(c:Category)
            MATCH (n)-[:PUBLISHED_BY]->(p:Publisher)
            
            {self.__return_template()}
            LIMIT {limit_no}
            """

        raise ValueError(f"지원하지 않는 템플릿: {self}")


if __name__ == "__main__":
    # 사용 예시: 카테고리로 뉴스 검색

    query = CypherQueryTemplates.NEWS_BY_CATEGORY.build(
        category_name="경제", limit_no=3)

    logger.info(query)