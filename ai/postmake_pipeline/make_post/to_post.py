from langchain_core.documents import Document

from common.connection import Connection, PGVectorStore, get_cursor
from common.logging_config import set_logging

logger = set_logging()


def to_post(result: dict, shop_data: dict) -> str:
    """결과를 게시글로 저장한다."""
    try:
        title = str(result.get("title") or "").strip().splitlines()[0][:100]
        content = str(result.get("post") or "").strip()
        tag = "# ".join(result.get("keyword", []))[:100]

        if not title or not content:
            logger.error(
                f"to_post validation failed | title_len={len(title)} | "
                f"content_len={len(content)} | crawling_id={shop_data.get('crawling_id')}"
            )
            return None

        query = """
        INSERT INTO posts (
            title, content, created_at, modify_at, status_cd, post_cd,
            category_cd, map_id, shop_id, crawling_id, tag
        )
        VALUES (%s, %s, NOW(), NOW(), %s, %s, %s, %s, %s, %s, %s)
        RETURNING post_id
        """
        cursor = get_cursor(query, (
            title,
            content,
            "ST01",
            "PT03",
            shop_data["category_cd"],
            shop_data["map_id"],
            shop_data["shop_id"],
            shop_data["crawling_id"],
            tag,
        ))
        row = cursor.fetchone() if cursor else None
        logger.info(
            f"to_post inserted | post_id={row['post_id'] if row else None} | "
            f"shop_id={shop_data.get('shop_id')}"
        )
        return row["post_id"] if row else None
    except Exception as e:
        logger.error(f"to_post error | Error={e} | crawling_id={shop_data.get('crawling_id')}")
        Connection().get_connection().rollback()
        return None


def to_post_vector(result: dict, shop_data: dict, post_id: int, keyword_data: list):
    """결과를 post_vector 컬렉션에 저장한다."""
    try:
        metadata = "#"+result["metadata"].copy() if isinstance(result.get("metadata"), dict) else {}
        metadata["post_id"] = post_id
        metadata["title"] = result.get("title")
        metadata["post_cd"] = "PT03"
        metadata["map_id"] = shop_data.get("map_id")
        metadata["shop_id"] = shop_data.get("shop_id")
        metadata["crawling_id"] = shop_data.get("crawling_id")
        metadata["shop"] = shop_data.get("title")
        metadata["category_cd"] = shop_data.get("category_cd")
        metadata["keywords"] = keyword_data
        metadata["tag"] = " #".join(result.get("keyword", []))[:100]
        document = Document(
            page_content=result["post"],
            metadata=metadata
        )
        vectorstore = PGVectorStore().get_vectorstore()
        vectorstore.add_documents([document])
        logger.info(f"to_post_vector inserted | post_id={post_id} | shop_id={shop_data.get('shop_id')}")
    except Exception as e:
        logger.error(f"to_post_vector error | Error={e} | crawling_id={shop_data.get('crawling_id')}")
        Connection().get_connection().rollback()
        return None
