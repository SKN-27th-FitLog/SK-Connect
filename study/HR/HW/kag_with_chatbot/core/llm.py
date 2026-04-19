"""
core/llm.py — LLM(대규모 언어 모델) 인스턴스 설정

Ollama 로컬 모델을 목적별로 2개의 인스턴스로 분리합니다:
    1. llm_extra : 추출/분류용 (temperature=0, 결정론적)
    2. llm_chat  : 대화/생성용 (temperature=0.7, 창의적)

[설계 원칙]
    - 환경 변수는 config.settings에서만 읽습니다.
    - 이 파일에서 load_dotenv()를 호출하지 않습니다.
    - 모델명과 컨텍스트 크기는 .env에서 설정 가능합니다.

[사용법]
    from core.llm import llm_extra, llm_chat
    # 또는 하위 호환: from core.llm import llm
"""

from langchain_ollama import ChatOllama
from config.settings import settings

# ─── 모델 및 컨텍스트 설정 (config에서 읽음) ────
MODEL = settings.OLLAMA_MODEL   # 기본: "gemma3:4b"
NUM_CTX = settings.NUM_CTX      # 기본: 8192 토큰


# ──────────────────────────────────────────────
# 1. Extraction용 LLM (결정론적)
# ──────────────────────────────────────────────
# 의도 파싱, 피드백 분류 등 정확한 구조화된 출력이 필요할 때 사용합니다.
# temperature=0으로 설정하여 동일 입력 → 동일 출력을 보장합니다.
llm_extra = ChatOllama(
    model=MODEL,
    temperature=0,          # 결정론적 출력
    num_ctx=NUM_CTX,        # 컨텍스트 윈도우 8k
    top_p=0.9,              # 누적 확률 기반 샘플링
    top_k=40,               # 상위 40개 토큰만 고려
    repeat_penalty=1.1,     # 반복 억제 패널티
)


# ──────────────────────────────────────────────
# 2. Chat/Generation용 LLM (창의적)
# ──────────────────────────────────────────────
# 사용자에게 보여줄 자연스러운 응답 생성에 사용합니다.
# temperature=0.7로 다양하고 풍부한 표현을 생성합니다.
llm_chat = ChatOllama(
    model=MODEL,
    temperature=0.7,        # 적당한 창의성
    num_ctx=NUM_CTX,        # 컨텍스트 윈도우 8k
    top_p=0.95,             # 더 넓은 샘플링 범위
    top_k=64,               # 상위 64개 토큰 고려
    repeat_penalty=1.1,     # 반복 억제 패널티
)


# ──────────────────────────────────────────────
# 하위 호환성 alias
# ──────────────────────────────────────────────
# 기존 코드에서 `from core.llm import llm`으로 사용하던 부분 지원
llm = llm_chat
