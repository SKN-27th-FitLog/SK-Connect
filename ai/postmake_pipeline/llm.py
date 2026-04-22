from langchain_ollama import ChatOllama
from typing import TypedDict, List
from llm import get_llm
from prompt import Prompt

def get_llm():
    return ChatOllama(
        model="gemma4:e4b",
        temperature=0.1,
        top_p=1.0,
        num_predict=500,
        keep_alive="20m"
    )

# 게시글 생성
#gemma4:e4b

#embedding

#similarity_search

#conditional_edge

class State(TypedDict):
    data: dict
    post: str
    embedding: List[float]
    is_unique: bool

def generate_node():
    llm = get_llm()
    prompt = Prompt()
    return llm.invoke(prompt)