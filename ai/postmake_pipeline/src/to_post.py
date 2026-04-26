from langchain_core.documents import Document

from dotenv import load_dotenv
from pathlib import Path
import os
from langchain_postgres.vectorstores import PGVector
from langchain_huggingface import HuggingFaceEmbeddings
from psycopg2 import connect
from src.logging_config import set_logging
logger = set_logging()

env_path = Path(__file__).resolve().parents[3] / "database" / ".env"
load_dotenv(env_path, override=True)


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

class Connection(metaclass=Singleton):
    def __init__(self):
        self.connection = connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            database=os.getenv("SERVICE_DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
        )

    def get_connection(self):
        return self.connection

class PGVectorStore(metaclass=Singleton):
    """vectorstore를 반환"""
    def __init__(self):
        model_kwargs = {}
        hf_token = os.getenv("HF_TOKEN")
        if hf_token:
            model_kwargs["token"] = hf_token

        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-mpnet-base-v2",
            model_kwargs=model_kwargs,
        )
        self.vectorstore = PGVector(
            embeddings=embeddings,
            connection=os.getenv("POSTGRES_URL"),
            collection_name="post_vector",
            embedding_length=768,
        )
        # 컬렉션/테이블 초기화 보장 (없으면 생성)
        self.vectorstore.create_vector_extension()
        self.vectorstore.create_tables_if_not_exists()
        self.vectorstore.create_collection()
    def get_vectorstore(self):
        return self.vectorstore

def get_vectorstore():
    return PGVectorStore().get_vectorstore()

def get_connection():
    return Connection().get_connection()

def to_post(result:dict):
    """결과를 게시글로 저장"""
    try:
        title = (result.get("title") or "").strip()
        keywords = (result.get("keywords") or "").strip()
        map_id = result.get("map_id")

        # DB 스키마(varchar(100))에 맞춰 길이를 보정
        if len(title) > 100:
            title = title[:100]
        if len(keywords) > 100:
            keywords = keywords[:100]

        query = """
        INSERT INTO posts (
            title,
            content,
            created_at,
            modify_at,
            status_cd,
            post_cd,
            category_cd,
            map_id,
            crawling_id,
            tag
        )
        SELECT
            %s, %s, NOW(), NOW(), %s, %s, %s, %s, %s, %s
        WHERE NOT EXISTS (
            SELECT 1
            FROM posts p
            WHERE p.title = %s
            AND (
                p.map_id = %s
                OR (p.map_id IS NULL AND %s IS NULL)
            )
        )
        RETURNING post_id
        """
        cursor = get_connection().cursor()
        cursor.execute(
            query,
            (
                title,
                result.get("content"),
                "ST01",
                "PT01",
                result.get("category_cd"),
                map_id,
                result.get("crawling_id"),
                keywords,
                title,
                map_id,
                map_id,
            ),
        )
        row = cursor.fetchone()
        get_connection().commit()
        return row[0] if row else None

    except Exception as e:
        logger.error(f"Error={e} | crawling_id={result['crawling_id']}")
        get_connection().rollback()
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
        vectorstore = get_vectorstore()
        vectorstore.add_documents([document])

    except Exception as e:
        logger.error(f"Error={e} | crawling_id={result['crawling_id']}")
        return False
    return True
