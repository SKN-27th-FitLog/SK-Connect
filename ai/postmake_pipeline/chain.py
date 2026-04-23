from llm import get_llm
from prompt import Prompt


def chain(data: str, type: str):
    llm = get_llm()
    prompt = Prompt(data=data).get_prompt(type=type)
    return llm.invoke(prompt)