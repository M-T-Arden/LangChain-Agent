from langchain.agents import create_agent
from langchain_ollama import ChatOllama

model = ChatOllama(
    model="qwen2.5-coder:7b",
    base_url="http://localhost:11434", # 显式指向映射出来的本地端口
)

@tool
def get_weather(city: str) -> str:
    """获取指定城市的天气。"""
    return f"{city}总是阳光明媚！"

tools=[get_weather]

agent = create_agent(
    model=model,
    tools=tools,
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "What's the weather in San Francisco?"}]}
)
print(result["messages"][-1].content_blocks)

