from typing import Optional, Any
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from langchain_core.language_models.chat_models import BaseChatModel
from common.util import get_env_var
from common.members import LLMProvider

def get_llm(
    provider: str = LLMProvider.GROQ.value,
    model_name: str = "llama-3.3-70b-versatile",
    temperature: float = 0.1,
    top_p: float = 1.0,
    frequency_penalty: float = 0.0,
    presence_penalty: float = 0.0,
) -> BaseChatModel:
    """
    제공자에 따른 ChatModel 인스턴스를 반환합니다.
    프로젝트 요구사항에 따라 기본값은 Groq입니다.
    """
    if provider == LLMProvider.GROQ.value:
        api_key: str = get_env_var("GROQ_API_KEY")
        return ChatGroq(
            model_name=model_name,
            temperature=temperature,
            api_key=api_key,
            model_kwargs={
                "top_p": top_p,
                "frequency_penalty": frequency_penalty,
                "presence_penalty": presence_penalty,
            }
        )
    elif provider == LLMProvider.OLLAMA.value:
        base_url: str = get_env_var("OLLAMA_BASE_URL", "http://localhost:11434")
        return ChatOllama(
            model=model_name,
            temperature=temperature,
            base_url=base_url,
            # Ollama 파라미터 설정
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
        )
    else:
        raise ValueError(f"지원하지 않는 제공자입니다: {provider}")
