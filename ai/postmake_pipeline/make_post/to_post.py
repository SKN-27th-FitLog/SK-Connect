from langchain_core.documents import Document
from common.connection import Connection, PGVectorStore
from common.logging_config import set_logging
logger = set_logging()



def to_post(result:dict):
    """결과를 게시글로 저장"""
    try:
        pass

    except Exception as e:
        logger.error(f"Error={e} | crawling_id={result['crawling_id']}")
        Connection().get_connection().rollback()
        return None

def to_post_vector(result:dict, post_id:int):
    """결과를 post_vector 테이블에 저장"""
    try:
        metadata = result["metadata"].copy() if isinstance(result.get("metadata"), dict) else {}
        metadata["post_id"] = post_id
        metadata["map_id"] = result.get("map_id")
        document = Document(
            page_content=result["content"],
            metadata=metadata
        )
        vectorstore = PGVectorStore().get_vectorstore()
        vectorstore.add_documents([document])
    except Exception as e:
        logger.error(f"Error={e} | crawling_id={result['crawling_id']}")
        Connection().get_connection().rollback()
        return None
