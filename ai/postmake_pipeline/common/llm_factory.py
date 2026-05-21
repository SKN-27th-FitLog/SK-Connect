from langchain_ollama import ChatOllama
from langchain_groq import ChatGroq
from functools import lru_cache


@lru_cache(maxsize=1)
def get_llm():
    """Return the shared post pipeline LLM client."""
    return ChatOllama(
        model="gemma4:e4b",
        temperature=0.3,
        keep_alive="60m",
    )


@lru_cache(maxsize=1)
def get_post_make_llm():
    return ChatOllama(
        model = 'qwen3.5:4b',
        keep_alive="60m",

    )


@lru_cache(maxsize=1)
def get_regenerate_llm():
    return ChatGroq(
        model = 'openai/gpt-oss-120b',
        keep_alive="60m",
    )
