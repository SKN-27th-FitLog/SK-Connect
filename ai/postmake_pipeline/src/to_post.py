from langchain_core.documents import Document

from dotenv import load_dotenv
from pathlib import Path
import os
import re
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

class PGVectorStore:
    """vectorstore를 반환"""
    def __init__(self, collection_name: str = "post_vector"):
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
            collection_name=collection_name,
            embedding_length=768,
        )
        # 컬렉션/테이블 초기화 보장 (없으면 생성)
        self.vectorstore.create_vector_extension()
        self.vectorstore.create_tables_if_not_exists()
        self.vectorstore.create_collection()
    def get_vectorstore(self):
        return self.vectorstore


_VECTORSTORE_CACHE: dict[str, PGVectorStore] = {} # 벡터 저장소

def _collection_name_by_category(category_cd: str | None) -> str:
    """category_cd별 컬렉션명 생성"""
    if not category_cd: # category_cd가 없으면 기본 컬렉션명 반환
        return "post_vector_unknown"
    normalized = re.sub(r"[^a-zA-Z0-9_]", "_", str(category_cd)).lower() # category_cd를 정규화
    return f"post_vector_{normalized}"


def get_vectorstore(category_cd: str | None = None):
    collection_name = _collection_name_by_category(category_cd)
    if collection_name not in _VECTORSTORE_CACHE:
        _VECTORSTORE_CACHE[collection_name] = PGVectorStore(collection_name=collection_name)
    return _VECTORSTORE_CACHE[collection_name].get_vectorstore()

def get_connection():
    return Connection().get_connection()

def to_post(result:dict):
    """결과를 게시글로 저장"""
    try:
        title = (result.get("title") or "").strip()
        keywords = (result.get("keywords") or "").strip()
        map_id = result.get("map_id")
        connection = get_connection()
        cursor = connection.cursor()

        # DB 스키마(varchar(100))에 맞춰 길이를 보정
        if len(title) > 100:
            title = title[:100]
        if len(keywords) > 100:
            keywords = keywords[:100]

        # 동일 map_id + title 기존 게시글이 있으면 벡터/원본을 삭제하고 교체 저장
        if map_id is not None and title:
            cursor.execute(
                """
                SELECT post_id
                FROM posts
                WHERE LOWER(TRIM(title)) = LOWER(TRIM(%s))
                  AND map_id = %s
                  AND post_cd = %s
                ORDER BY modify_at DESC, post_id DESC
                LIMIT 1
                """,
                (title, map_id, "PT01"),
            )
            existing = cursor.fetchone()
            if existing:
                old_post_id = existing[0]
                cursor.execute(
                    """
                    DELETE FROM langchain_pg_embedding
                    WHERE (cmetadata->>'post_id')::bigint = %s
                    """,
                    (old_post_id,),
                )
                cursor.execute("DELETE FROM posts WHERE post_id = %s", (old_post_id,))

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
        RETURNING post_id
        """
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
            ),
        )
        row = cursor.fetchone()
        connection.commit()
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
        vectorstore = get_vectorstore(result.get("category_cd"))
        vectorstore.add_documents([document])

    except Exception as e:
        logger.error(f"Error={e} | crawling_id={result['crawling_id']}")
        return False
    return True
