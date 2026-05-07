from langchain_core.documents import Document
from common.connection import Connection, PGVectorStore
from common.logging_config import set_logging
from common.connection import get_cursor

logger = set_logging()


def to_post(result: dict, shop_data: dict) -> str:
    """결과를 게시글로 저장"""
    try:
        query = """
        INSERT INTO posts (
            title, content, created_at, modify_at, status_cd, post_cd,
            category_cd, map_id, shop_id, crawling_id, tag
        )
        VALUES (%s, %s, NOW(), NOW(), %s, %s, %s, %s, %s, %s, %s)
        RETURNING post_id
        """
        cursor = get_cursor(query, (
            result["title"],
            result["post"],
            "ST01",
            "PT03",
            shop_data["category_cd"],
            shop_data["map_id"],
            shop_data["shop_id"],
            shop_data["crawling_id"],
            "# ".join(result.get("keyword", [])),
        ))
        row = cursor.fetchone() if cursor else None
        return row["post_id"] if row else None
    except Exception as e:
        logger.error(f"Error={e} | crawling_id={shop_data.get('crawling_id')}")
        Connection().get_connection().rollback()
        return None


def to_post_vector(result: dict, shop_data: dict, post_id: int, keyword_data: list):
    """결과를 post_vector 테이블에 저장"""
    try:
        metadata = result["metadata"].copy() if isinstance(result.get("metadata"), dict) else {}
        metadata["post_id"] = post_id
        metadata["map_id"] = shop_data.get("map_id")
        metadata["shop"] = shop_data.get("title")
        metadata["category_cd"] = shop_data.get("category_cd")
        metadata["keywords"] = keyword_data
        document = Document(
            page_content=result["post"],
            metadata=metadata
        )
        vectorstore = PGVectorStore().get_vectorstore()
        vectorstore.add_documents([document])
    except Exception as e:
        logger.error(f"Error={e} | crawling_id={shop_data.get('crawling_id')}")
        Connection().get_connection().rollback()
        return None
