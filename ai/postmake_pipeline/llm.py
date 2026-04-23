from langchain_ollama import ChatOllama
from langchain_huggingface import HuggingFaceEmbeddings
from typing import TypedDict, List
from llm import get_llm
from prompt import Prompt
from dotenv import load_dotenv
import os
load_dotenv()


def get_llm():
    return ChatOllama(
        model="gemma4:e4b",
        temperature=0.1,
        top_p=1.0,
        num_predict=500,
        keep_alive="20m"
    )


class State(TypedDict):
    data: dict
    post: str
    embedding: List[float]
    is_unique: bool

def embedding_node(state: State):
    embeddings_huggingface = HuggingFaceEmbeddings(
        model_name = 'google/embeddinggemma-300m',
        token = os.getenv("HF_TOKEN"),
    )
    return {
        "embedding": embeddings_huggingface.embed_query(state["data"]["content"])
    }

def similarity_search_node(state: State):
    pass

def mk_post_node():
    llm = get_llm()
    prompt = Prompt()
    return llm.invoke(prompt)