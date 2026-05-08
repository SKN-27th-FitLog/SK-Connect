from dotenv import load_dotenv
from pathlib import Path
from psycopg2 import connect
from psycopg2.extras import RealDictCursor
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_postgres.vectorstores import PGVector
import os
import time
from common.logging_config import set_logging
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
        self.connection.autocommit = True

    def get_connection(self):
        return self.connection



class PGVectorStore(metaclass=Singleton):
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

def get_cursor(query:str, params=None):
    try:
        connection = Connection().get_connection()
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query, params)
        return cursor
    except Exception as e:
        logger.error(f"Error={e} | time={time.time()}")
        return None
