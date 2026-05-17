from langchain_core.documents import Document

from common.connection import Connection, PGVectorStore, get_cursor
from common.logging_config import set_logging

logger = set_logging()


def to_post(result: dict, shop_data: dict) -> str:
    """결과를 게시글로 저장한다."""
    try:
        # DB 컬럼 길이와 빈 값 저장을 고려해 제목/본문/태그를 먼저 정리한다.
        title = str(result.get("title") or "").strip().splitlines()[0][:100]
        content = str(result.get("post") or "").strip()
        tag = "# ".join(result.get("keyword", []))[:100]

        # 제목 또는 본문이 비어 있으면 게시글로 저장하지 않는다.
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
        row = None
        if cursor:
            row = cursor.fetchone()
        post_id = None
        if row:
            post_id = row["post_id"]
        logger.info(
            f"to_post inserted | post_id={post_id} | "
            f"shop_id={shop_data.get('shop_id')}"
        )
        return post_id
    except Exception as e:
        logger.error(f"to_post error | Error={e} | crawling_id={shop_data.get('crawling_id')}")
        Connection().get_connection().rollback()
        return None


def to_post_vector(
    result: dict,
    shop_data: dict | list[dict],
    post_id: int,
    keyword_data: list,
    keyword_stats: list[dict],
):
    """결과를 post_vector 컬렉션에 저장한다."""
    try:
        # 호출부가 매장 묶음 전체를 넘겨도 첫 row 기준 metadata로 맞춘다.
        shop_rows = [shop_data]
        if isinstance(shop_data, list):
            shop_rows = shop_data
            if shop_data:
                shop_data = shop_data[0]
            elif not shop_data:
                shop_data = {}

        # 검색/추천에서 필터링할 수 있도록 게시글과 매장 정보를 metadata에 함께 넣는다.
        metadata = {}
        if isinstance(result.get("metadata"), dict):
            metadata = result.get("metadata", {}).copy()
        metadata["post_id"] = post_id
        metadata["title"] = result.get("title")
        metadata["post_cd"] = "PT03"
        metadata["map_id"] = shop_data.get("map_id")
        metadata["shop_id"] = shop_data.get("shop_id")
        metadata["crawling_id"] = shop_data.get("crawling_id")
        metadata["shop"] = shop_data.get("title")
        metadata["category_cd"] = shop_data.get("category_cd")
        metadata["selected_keywords"] = keyword_data
        metadata["keyword_stats"] = keyword_stats
        metadata["used_crawling_ids"] = [
            row.get("crawling_id") for row in shop_rows if row.get("crawling_id")
        ]
        metadata["latest_crawling_created_at"] = max((
            str(row.get("crawling_created_at") or row.get("created_dt") or "")
            for row in shop_rows
            if row
        ), default="")
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
