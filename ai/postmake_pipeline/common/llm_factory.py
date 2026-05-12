from langchain_ollama import ChatOllama

_llm = None


def get_llm():
    """Return the shared post pipeline LLM client."""
    global _llm
    if _llm is None:
        _llm = ChatOllama(
            model="gemma4:e4b",
            temperature=0.3,
            keep_alive="60m",
        )
    return _llm
