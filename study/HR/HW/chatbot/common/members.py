from enum import Enum

class LLMProvider(Enum):
    """LLM 제공자 정의"""
    GROQ = "Groq"
    OLLAMA = "Ollama"

class ShortAnswerTask(Enum):
    """단답 화면 작업 종류"""
    CONCEPT = "개념 설명"
    SUMMARY = "문장 요약"
    KEYWORD = "키워드 추출"
    TRANS = "언어 번역"
    CODE = "코드 작성"
    ETC = "기타"

class OutputStyle(Enum):
    """출력 스타일 정의"""
    EASY = "쉽게"
    DETAIL = "자세히"
    LIST = "목록형"
    EXAMPLE = "예시 포함"
    EXPERT = "전문가풍"
