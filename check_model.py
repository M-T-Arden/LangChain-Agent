""" check if model supports tool calls """
from langchain_ollama import ChatOllama
from langchain.tools import tool

model = ChatOllama(model="llama3.1:8b", base_url="http://localhost:11434")

@tool
def get_weather(city: str) -> str:
    """获取指定城市的天气。"""
    return f"{city}总是阳光明媚！"

# 关键：显式 bind_tools
model_with_tools = model.bind_tools([get_weather])

response = model_with_tools.invoke("What's the weather in Tokyo?")

print("type:", type(response))
print("content:", response.content)
print("tool_calls:", response.tool_calls)  # if it's empty, it doesn't support natively.
