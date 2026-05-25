from langchain_ollama import ChatOllama
from dotenv import load_dotenv
from functools import lru_cache
from pathlib import Path

env_path = Path(__file__).resolve().parents[3] / "database" / ".env"
load_dotenv(env_path, override=False)
pipeline_env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(pipeline_env_path, override=False)

@lru_cache(maxsize=1)
def get_post_generation_llm():
    """Return the shared LLM client for initial post generation and regeneration."""
    return ChatOllama(
        model="gemma3:4b",
        temperature=0.5,
        keep_alive="60m",
    )


@lru_cache(maxsize=1)
def get_evaluation_llm():
    return ChatOllama(
        model="gemma4:e4b",
        temperature=0,
        keep_alive="60m",
    )
