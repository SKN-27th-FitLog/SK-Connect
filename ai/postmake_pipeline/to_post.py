from langchain_core.documents import Document
import os
from langchain_postgres.vectorstores import PGVector
from psycopg2 import connect
from logging_config import set_logging
logger = set_logging()

def get_vectorstore():
    """vectorstore를 반환"""
    return PGVector(
        connection_string=os.getenv("POSTGRES_URL"),
        collection_name="post_vector"
    )

def to_post(result:dict):
    """결과를 post_vector 테이블에 저장"""
    try:
        document = Document(
            page_content=result["content"],
            metadata=result["metadata"]
        )
        vectorstore = get_vectorstore()
        vectorstore.add_documents([document])
    except Exception as e:
        logger.error(f"Error={e} | crawling_id={result['crawling_id']}")
        return False
    return True