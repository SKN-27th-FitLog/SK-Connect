from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# 1. 단답 화면 프롬프트
# 프롬프트에 대한 내용이 출력이 되어야함 -> 이유: task와 output_style을 어떻게 입력해야할지 애매함
SHORT_ANSWER_SYSTEM_PROMPT = """당신은 친절하고 정확하게 답변하는 도우미입니다. 
사용자의 요청을 목적({task})과 스타일({output_style})에 맞춰 최선을 다해 처리하세요."""

def get_short_answer_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([
        ("system", SHORT_ANSWER_SYSTEM_PROMPT),
        ("human", "{user_input}")
    ])

# 2. 챗봇 화면 프롬프트
CHATBOT_SYSTEM_PROMPT = """당신은 사용자의 이전 대화를 기억하며, 문맥을 유지해서 답하는 AI 챗봇입니다.
항상 친절하고 도움이 되는 방향으로 대화하세요."""

def get_chatbot_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([
        ("system", CHATBOT_SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{user_input}")
    ])

# 3. Few-shot 화면 프롬프트
# 프롬프트에 대한 내용이 출력이 되어야함 -> 이유: 예시를 어떻게 입력해야할지 애매함
FEWSHOT_SYSTEM_PROMPT = """당신은 주어진 예시의 형식을 완벽하게 따라 답변하는 도우미입니다.
사용자가 제공한 예시들의 톤, 매너, 응답 구조를 그대로 유지하세요."""

def get_fewshot_prompt(examples_str: str) -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([
        ("system", FEWSHOT_SYSTEM_PROMPT),
        ("system", f"아래는 당신이 따라야 할 예시들입니다:\n\n{examples_str}"),
        ("human", "{user_input}")
    ])
