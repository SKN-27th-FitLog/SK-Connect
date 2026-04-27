from langchain_ollama import ChatOllama


def get_llm():
    """파이프라인 공통 LLM 설정"""
    return ChatOllama(
        model="gemma4:e4b",
        temperature=0.2,
        keep_alive="20m",
    )
