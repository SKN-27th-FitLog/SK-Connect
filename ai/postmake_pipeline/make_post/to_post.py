from langchain_core.documents import Document
from common.connection import Connection, PGVectorStore
from common.logging_config import set_logging
from common.connection import get_cursor
logger = set_logging()



def to_post(result:dict, shop_data:dict) -> str:
    """결과를 게시글로 저장"""
    try:
        query = """
        INSERT INTO analysis (title, content, status_cd, post_cd, category_cd, map_id, shop_id, crawling_id, tag
        VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING post_id
        """
        post_id = get_cursor(query, result['title'], result['content'], "ST01", shop_data['post_cd'], \
            shop_data['category_cd'], shop_data['map_id'], shop_data['shop_id'], shop_data['crawling_id'])
        return post_id
    except Exception as e:
        logger.error(f"Error={e} | crawling_id={result['crawling_id']}")
        Connection().get_connection().rollback()
        return None

def to_post_vector(result:dict, shop_data:dict, post_id:int, keyword_data:list):
    """결과를 post_vector 테이블에 저장"""
    try:
        metadata = result["metadata"].copy() if isinstance(result.get("metadata"), dict) else {}
        metadata["post_id"] = post_id
        metadata["map_id"] = result.get("map_id")
        metadata['shop'] = shop_data.get('title')
        metadata['category_cd'] = shop_data.get('category_cd')
        metadata['keywords'] = keyword_data.get()
        document = Document(
            page_content=result["content"],
            metadata=metadata
        )
        vectorstore = PGVectorStore().get_vectorstore()
        vectorstore.add_documents([document])
        # 저장한 post의 id를 리턴

    except Exception as e:
        logger.error(f"Error={e} | crawling_id={result['crawling_id']}")
        Connection().get_connection().rollback()
        return None
