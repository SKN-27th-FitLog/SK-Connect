from langchain_ollama import ChatOllama

model = ChatOllama(
    model="gemma4:e4b",
    temperature=0.1,
    top_p=1.0,
    num_predict=500,
    keep_alive="20m"
)
# 게시글 생성
#gemma4:e4b

#embedding
